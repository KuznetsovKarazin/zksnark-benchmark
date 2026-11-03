#!/usr/bin/env python3
"""PETs4DeFi ECON-04: bounded, reproducible network-cost accounting.

Stdlib only; never interprets missing provider fees as zero.
Technical inputs are archived synthetic workloads; no contracts or proofs run.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

getcontext().prec = 30
D = Decimal

PINNED = {
    "implementation_snapshot_commit": "9e5cde998cf15a2fda24d54a2bfad288b107642f",
    "economic_inputs_protocol_commit": "eb9244439fb798aae359ee03f270870fc8e5d7be",
    "measurement_source_commit": "8e71e52fbfef382b96b75266a7c78d816c7e1751",
}
INPUT_NAMES = ["frequency_workload_costs.csv", "frequency_event_counts.csv", "frequency_decisions.csv"]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def as_decimal(value: Any) -> Decimal:
    return D(str(value))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def to_str(v: Any) -> str | None:
    return str(v) if v is not None else None


@dataclass(frozen=True)
class Config:
    horizon_days: int
    policy: str
    services: int
    population_n: int
    issuers: int
    credential_days: int
    auth_ttl_days: int
    activity_examples: tuple[int, ...]
    user_share_b2: Decimal
    pricing_scenario: str

    @staticmethod
    def load(path: Path) -> "Config":
        raw = json.loads(path.read_text(encoding="utf-8"))
        cfg = Config(
            horizon_days=int(raw["horizon_days"]), policy=str(raw["policy"]),
            services=int(raw["services"]), population_n=int(raw["population_n"]),
            issuers=int(raw["issuers"]), credential_days=int(raw["credential_days"]),
            auth_ttl_days=int(raw["auth_ttl_days"]),
            activity_examples=tuple(int(v) for v in raw["activity_examples"]),
            user_share_b2=D(str(raw["user_share_b2"])),
            pricing_scenario=str(raw["pricing_scenario"]),
        )
        if cfg.population_n <= 0:
            raise ValueError("N must be >0 for F/N and required margin; N=0 is undefined")
        if not (D(0) <= cfg.user_share_b2 <= D(1)):
            raise ValueError("alpha must be in [0,1]")
        if not cfg.activity_examples or any(n <= 0 for n in cfg.activity_examples):
            raise ValueError("zero-activity trace is not supplied; do not silently fabricate one")
        if cfg.pricing_scenario not in {"p50", "p90"}:
            raise ValueError("Choose exactly one archived pricing scenario p50 or p90")
        return cfg


@dataclass(frozen=True)
class SelectedWorkload:
    n: int
    context_id: str
    unchecked: dict[str, str]
    signed: dict[str, str]
    zk: dict[str, str]
    decision: dict[str, str]

    def gas(self, variant: dict[str, str]) -> Decimal:
        return D(variant["user_transaction_gas_per_user"])

    def price_gwei(self, scenario: str) -> Decimal:
        key = "fee_p50_wei_per_gas" if scenario == "p50" else "fee_p90_wei_per_gas"
        return D(self.decision[key]) / D(10)**9

    def euro(self, gas: Decimal, scenario: str) -> Decimal:
        return gas * self.price_gwei(scenario) * D(self.decision["eur_per_eth"]) / D(10)**9


def select_workload(n: int, cfg: Config, work: list[dict[str, str]], decisions: list[dict[str, str]], events: list[dict[str, str]]) -> SelectedWorkload:
    candidate = [x for x in decisions if x["accesses"] == str(n) and x["policy"] == cfg.policy]
    if len(candidate) != 1:
        raise ValueError(f"Expected exactly one selection for n={n}, found {len(candidate)}")
    decision = candidate[0]
    cid = decision["context_id"]
    ws = [x for x in work if x["context_id"] == cid and x["policy"] == cfg.policy]
    if len(ws) != 5:
        raise ValueError(f"Expected 5 technical methods for {cid}, found {len(ws)}")
    by_variant = {x["variant"]: x for x in ws}
    if len(by_variant) != 5 or set(by_variant) != {"unchecked", "signed_direct", "signed_cache", "zk_direct", "zk_cache"}:
        raise ValueError(f"Unknown technical method inventory for {cid}")
    signed = by_variant[decision["selected_signed_variant"]]
    zk = by_variant[decision["selected_zk_variant"]]
    if signed["variant"] not in {"signed_direct", "signed_cache"} or zk["variant"] not in {"zk_direct", "zk_cache"}:
        raise ValueError("Selected implementations have wrong technology family")
    def gas(x: dict[str,str]) -> Decimal:
        return D(x["user_transaction_gas_per_user"])
    if gas(signed) != min(gas(by_variant["signed_direct"]), gas(by_variant["signed_cache"])):
        raise AssertionError("Signed option does not minimize user transaction gas")
    if gas(zk) != min(gas(by_variant["zk_direct"]), gas(by_variant["zk_cache"])):
        raise AssertionError("ZK option does not minimize user transaction gas")
    if gas(signed) != D(decision["signed_user_transaction_gas_per_user"]):
        raise AssertionError("Decision signed gas mismatch")
    if gas(zk) != D(decision["zk_user_transaction_gas_per_user"]):
        raise AssertionError("Decision ZK gas mismatch")
    if gas(signed)-gas(by_variant["unchecked"]) != D(decision["signed_minus_unchecked_user_gas"]):
        raise AssertionError("Decision signed increment mismatch")
    if gas(zk)-gas(signed) != D(decision["zk_minus_signed_user_gas"]):
        raise AssertionError("Decision privacy increment mismatch")
    for x in ws:
        if any(int(x[k]) != v for k,v in [
            ("horizon_days", cfg.horizon_days),("apps",cfg.services),
            ("population",cfg.population_n),("issuers",cfg.issuers),
            ("validity_days",cfg.credential_days),("auth_ttl_days",cfg.auth_ttl_days),
        ]):
            raise AssertionError("Mismatch with 90-day fixed service scenario")
        erows = [e for e in events if e["context_id"]==cid and e["policy"]==cfg.policy and e["variant"]==x["variant"]]
        gas_from_events = sum((D(e["projected_gas_per_user"]) for e in erows), D(0))
        if gas_from_events != gas(x):
            raise AssertionError(f"Event total disagrees with {x['variant']}: {gas_from_events} vs {gas(x)}")
        event_count = sum((D(e["event_count_per_user"]) for e in erows if e["event"]!="approve"),D(0))
        if event_count != D(n):
            raise AssertionError(f"First/repeat accesses do not add to n={n} for {x['variant']}")
        if D(x["full_authorizations_per_user"]) + D(x["cache_hits_per_user"]) != D(n) and x["variant"] != "unchecked":
            raise AssertionError("Authorization + cache hits must equal accesses")
        if x["variant"] in {"signed_cache", "zk_cache"}:
            if D(x["reauthorizations_per_user"])+D(1) != D(x["full_authorizations_per_user"]):
                raise AssertionError("One initial authorization + reauth count mismatch")
    return SelectedWorkload(n,cid,by_variant["unchecked"],signed,zk,decision)


def accounting(A: Decimal, base: Decimal, alpha: Decimal, n_users: int) -> dict[str, Any]:
    """Return only measured/attributed network components, never imaginary total cost."""
    if n_users <= 0:
        raise ValueError("N=0: F/N undefined; cannot report required net margin")
    if A < 0:
        raise ValueError("Negative incremental access pool requires a separate boundary review")
    if alpha < 0 or alpha > 1:
        raise ValueError("alpha must be in [0,1]")
    rebate = (D(1)-alpha)*A
    user_paid_upfront = base + A
    user_final_known = user_paid_upfront - rebate
    service_network_expense = rebate
    if user_final_known + service_network_expense != user_paid_upfront:
        raise AssertionError("Network cost conservation broken")
    return {
        "allocation_pool_A_eur": to_str(A),
        "common_unchecked_deposit_gas_eur": to_str(base),
        "user_share_alpha": to_str(alpha),
        "user_network_payment_upfront_eur": to_str(user_paid_upfront),
        "service_conditional_reimbursement_eur": to_str(rebate),
        "user_network_cost_after_cash_equivalent_reimbursement_eur": to_str(user_final_known),
        "service_known_network_cost_eur": to_str(service_network_expense),
        "external_total_network_cost_eur": to_str(user_paid_upfront),
        "required_margin_expression": f"m_required = s_other + {rebate} EUR − f + F/{n_users}",
        "user_payment_expression": f"U = {user_final_known} EUR + u_other + f",
        "service_variable_expense_expression": f"S = {rebate} EUR + s_other",
        "unknown_costs_status": "u_other, s_other, f, m, F, v, active user time, reimbursement mechanism/overhead are unresolved; not assumed zero",
    }


def produce(cfg: Config, input_dir: Path) -> tuple[list[dict[str,str]], dict[str,Any]]:
    src = {name: rows(input_dir/name) for name in INPUT_NAMES}
    results = []
    details=[]
    for n in cfg.activity_examples:
        ws=select_workload(n,cfg,src["frequency_workload_costs.csv"],src["frequency_decisions.csv"],src["frequency_event_counts.csv"])
        base=ws.euro(ws.gas(ws.unchecked),cfg.pricing_scenario)
        selected=[]
        for name,variant,alpha in [("B0",ws.signed,D(1)),("B1",ws.zk,D(1)),("B2",ws.zk,cfg.user_share_b2)]:
            A=ws.euro(ws.gas(variant)-ws.gas(ws.unchecked),cfg.pricing_scenario)
            out=accounting(A,base,alpha,cfg.population_n)
            details.append({"workload_deposits":n,"regime":name,"variant":variant["variant"],**out})
            results.append({
                "context_id":ws.context_id,"deposits_per_user":str(n),"regime":name,
                "technical_variant":variant["variant"],"user_share_alpha":str(alpha),
                "transaction_gas_per_user":variant["user_transaction_gas_per_user"],
                "unchecked_gas_per_user":ws.unchecked["user_transaction_gas_per_user"],
                "full_authorizations_per_user":variant["full_authorizations_per_user"],
                "cache_hits_per_user":variant["cache_hits_per_user"],
                "credential_renewals_per_user":variant["credential_renewals_per_user"],
                "priced_fee_scenario":cfg.pricing_scenario,"fee_gwei":str(ws.price_gwei(cfg.pricing_scenario)),
                "eth_eur":ws.decision["eur_per_eth"],
                "common_unchecked_deposit_gas_eur":out["common_unchecked_deposit_gas_eur"],
                "allocation_pool_A_eur":out["allocation_pool_A_eur"],
                "service_conditional_reimbursement_eur":out["service_conditional_reimbursement_eur"],
                "user_network_payment_upfront_eur":out["user_network_payment_upfront_eur"],
                "user_network_cost_after_cash_equivalent_reimbursement_eur":out["user_network_cost_after_cash_equivalent_reimbursement_eur"],
                "service_known_network_cost_eur":out["service_known_network_cost_eur"],
                "external_total_network_cost_eur":out["external_total_network_cost_eur"],
                "unknown_extra_user_cost_eur":"unknown: u_other",
                "unknown_extra_service_cost_eur":"unknown: s_other",
                "fixed_fee_eur":"symbolic: f",
                "net_other_service_revenue_eur":"unknown: m",
                "fixed_service_cost_eur":"unknown: F",
                "required_net_margin_eur":out["required_margin_expression"],
                "required_privacy_benefit_eur":"U_private - U_B0 + v*(t_private-t_B0); t and v unknown",
                "reimbursement_implemented":"NO: conditional cash-equivalent transfer only",
            })
        if selected: raise AssertionError("Unexpected placeholder")
    meta={
        "project":"PETs4DeFi", "stage":"ECON-04 preliminary implementation; NOT ECON-05 sweep",
        "source_commits_supplied_by_technical_owner":PINNED,
        "input_file_sha256":{name:digest(input_dir/name) for name in INPUT_NAMES},
        "config":{"horizon_days":cfg.horizon_days,"policy":cfg.policy,"services":cfg.services,"population_n":cfg.population_n,
                  "issuers":cfg.issuers,"credential_days":cfg.credential_days,"auth_ttl_days":cfg.auth_ttl_days,
                  "activity_examples":list(cfg.activity_examples),"user_share_b2":str(cfg.user_share_b2),"pricing_scenario":cfg.pricing_scenario},
        "evidence_note":"Synthetic access frequencies plus measured/local gas units; not an empirical adoption or profitability estimate.",
        "currency_note":"ETH/EUR is archived scenario, not realized fee/FX; testnet budget not inferred.",
        "unknowns_note":"Other user/provider/operator costs, payout overhead, service margin, fixed costs, active time unresolved.",
        "review_note":"Requires second-person check; automated assertions are not independent scientific review.",
        "authoring_note":"AI-assisted coding, calculations and tests; source material from technical package; no contracts/proofs executed.",
        "row_count":len(results),
        "details":details,
    }
    return results,meta


def main()->None:
    base=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser(description="Run bounded ECON-04 network cost accounting")
    parser.add_argument("--config",type=Path,default=base/"run_config.json")
    parser.add_argument("--input-dir",type=Path,default=base/"inputs")
    parser.add_argument("--output-dir",type=Path,default=base/"results")
    args=parser.parse_args()
    cfg=Config.load(args.config)
    results,metadata=produce(cfg,args.input_dir)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    with (args.output_dir/"results.csv").open("w",newline="",encoding="utf-8") as fp:
        wr=csv.DictWriter(fp,fieldnames=list(results[0]));wr.writeheader();wr.writerows(results)
    (args.output_dir/"run_metadata.json").write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding="utf-8")
    for row in results:
        print(f"n={row['deposits_per_user']:>3}, {row['regime']}: {row['technical_variant']:<12} "
              f"gas={row['transaction_gas_per_user']:<12} A={D(row['allocation_pool_A_eur']):.6f} EUR "
              f"user net={D(row['user_network_cost_after_cash_equivalent_reimbursement_eur']):.6f} EUR "
              f"service subsidy={D(row['service_conditional_reimbursement_eur']):.6f} EUR")
    print("Saved:",args.output_dir/"results.csv")
    print("Saved:",args.output_dir/"run_metadata.json")

if __name__=="__main__":
    main()
