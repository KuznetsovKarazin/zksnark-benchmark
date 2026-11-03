#!/usr/bin/env python3
"""ECON-05 reproducible bounded gas-allocation sweep; Python stdlib only.

Imports the scientifically accepted ECON-04 source file unchanged.
All unknown off-chain expenses, revenue and active-user time stay symbolic.
"""
from __future__ import annotations
import csv
import json
from decimal import Decimal as D
from pathlib import Path
from economic_model import Config, PINNED, accounting, digest, rows, select_workload

BASE = Path(__file__).resolve().parent
INPUT_NAMES = ["frequency_workload_costs.csv", "frequency_event_counts.csv", "frequency_decisions.csv", "economic_sweep_plan.csv"]
FIELDS = [
 "scenario_id", "activity_deposits_per_user_90d", "fee_scenario", "eth_eur", "fee_gwei_per_gas",
 "population_n", "policy", "horizon_days", "baseline_signed_variant", "selected_zk_variant",
 "signed_full_authorizations", "signed_cache_hits", "zk_full_authorizations", "zk_cache_hits",
 "unchecked_gas_per_user", "signed_gas_per_user", "zk_gas_per_user",
 "user_share_alpha", "service_share_one_minus_alpha", "regime",
 "common_unchecked_network_cost_eur_user", "signed_access_pool_eur_user", "zk_access_pool_eur_user",
 "user_zw_network_upfront_eur_user", "user_network_after_cash_reimbursement_eur_user",
 "user_share_of_zk_pool_eur_user", "service_subsidy_eur_user",
 "service_subsidy_eur_population", "service_subsidy_eur_deposit", "user_network_difference_vs_B0_eur_user",
 "user_pool_difference_vs_B0_eur_user", "network_extra_resource_cost_zk_vs_signed_eur_user",
 "alpha_crit_user_network_indifference", "gas_only_user_not_more_expensive_than_B0",
 "incremental_service_coverage_needed_vs_B0_eur_user_if_other_terms_match",
 "minimum_m_required_expression", "incremental_m_required_vs_B0_expression", "required_user_benefit_expression",
 "gas_cost_conservation_error_eur_user", "unresolved_items", "cash_compensation_status"
]


def produce_sweep(config_path: Path=BASE/"econ05_config.json", input_dir: Path=BASE/"inputs"):
    cfg=json.loads(config_path.read_text(encoding="utf-8"))
    assert cfg["deposit_counts"]==[1,10,100], "Unapproved deposit counts: core sweep only"
    assert cfg["price_scenarios"]==["p50","p90"], "Both archived price cases required"
    shares=[D(x) for x in cfg["user_shares"]]
    assert shares==[D(0),D("0.25"),D("0.5"),D("0.75"),D(1)]
    baseline_cfg=Config.load(BASE/"run_config.json")
    if any([baseline_cfg.horizon_days!=cfg["horizon_days"], baseline_cfg.population_n!=cfg["population_n"],baseline_cfg.services!=cfg["services"],baseline_cfg.policy!=cfg["policy"],baseline_cfg.credential_days!=cfg["credential_days"],baseline_cfg.auth_ttl_days!=cfg["auth_ttl_days"],baseline_cfg.issuers!=cfg["issuers"]]):
        raise ValueError("ECON-05 configuration diverges from approved ECON-04 context")
    src={f:rows(input_dir/f) for f in INPUT_NAMES}
    plan={(int(row["accesses"]),D(row["private_user_share_alpha"])):row for row in src["economic_sweep_plan.csv"]}
    assert len(plan)==15, "Expected fifteen unique technical plan scenarios"
    out=[]; baselines=[]
    for n in cfg["deposit_counts"]:
        w=select_workload(n,baseline_cfg,src["frequency_workload_costs.csv"],src["frequency_decisions.csv"],src["frequency_event_counts.csv"])
        G0=w.gas(w.unchecked);Gs=w.gas(w.signed);Gz=w.gas(w.zk)
        for price in cfg["price_scenarios"]:
            C=w.euro(G0,price); As=w.euro(Gs-G0,price); Az=w.euro(Gz-G0,price)
            crit=As/Az
            b0=accounting(As,C,D(1),cfg["population_n"])
            baselines.append({"activity_deposits_per_user_90d":n,"fee_scenario":price,"signed_variant":w.signed["variant"],"signed_access_pool_eur_user":str(As),"common_unchecked_network_cost_eur_user":str(C),"user_B0_gas_eur_user":b0["user_network_cost_after_cash_equivalent_reimbursement_eur"],"user_B0_gas_eur_population":str((C+As)*D(cfg["population_n"]))})
            for alpha in shares:
                pl=plan[n,alpha]; scenario=f"n{n}-alpha{alpha.normalize()}"
                if pl["context_id"]!=w.context_id or pl["baseline_signed_variant"]!=w.signed["variant"] or pl["private_zk_variant"]!=w.zk["variant"]: raise AssertionError(f"Plan selection mismatch at n={n},a={alpha}")
                if D(pl["unchecked_gas_per_user_unpooled"])!=G0 or D(pl["baseline_access_pool_gas_per_user"])!=Gs-G0 or D(pl["private_access_pool_gas_per_user"])!=Gz-G0: raise AssertionError("Technical gas plan mismatch")
                price_suffix="fee_p50" if price=="p50" else "fee_p90"
                # Independently compare ALL named numeric fee columns to the source's frozen 15-case economic plan.
                for key,expected in {
                 f"unchecked_eur_{price_suffix}":C,
                 f"baseline_access_pool_eur_{price_suffix}":As,
                 f"private_access_pool_eur_{price_suffix}":Az,
                 f"private_user_pool_component_eur_{price_suffix}":alpha*Az,
                 f"private_service_pool_component_eur_{price_suffix}":(1-alpha)*Az
                }.items():
                    if abs(D(pl[key])-expected)>D("0.000000000000001"): raise AssertionError(f"Precomputed plan mismatch: {key}, n={n}, alpha={alpha}, price={price}")
                acc=accounting(Az,C,alpha,cfg["population_n"])
                R=(1-alpha)*Az
                user_pool=alpha*Az
                user_delta=user_pool-As
                row={
                 "scenario_id":pl["scenario_id"]+"-"+price,
                 "activity_deposits_per_user_90d":str(n),"fee_scenario":price,
                 "eth_eur":w.decision["eur_per_eth"],"fee_gwei_per_gas":str(w.price_gwei(price)),
                 "population_n":str(cfg["population_n"]),"policy":cfg["policy"],"horizon_days":str(cfg["horizon_days"]),
                 "baseline_signed_variant":w.signed["variant"],"selected_zk_variant":w.zk["variant"],
                 "signed_full_authorizations":w.signed["full_authorizations_per_user"],"signed_cache_hits":w.signed["cache_hits_per_user"],
                 "zk_full_authorizations":w.zk["full_authorizations_per_user"],"zk_cache_hits":w.zk["cache_hits_per_user"],
                 "unchecked_gas_per_user":str(G0),"signed_gas_per_user":str(Gs),"zk_gas_per_user":str(Gz),
                 "user_share_alpha":str(alpha),"service_share_one_minus_alpha":str(1-alpha),
                 "regime":"B1 ZK user-funded endpoint" if alpha==1 else "B2 conditional cash-equivalent reimbursement",
                 "common_unchecked_network_cost_eur_user":str(C),"signed_access_pool_eur_user":str(As),"zk_access_pool_eur_user":str(Az),
                 "user_zw_network_upfront_eur_user":str(C+Az),
                 "user_network_after_cash_reimbursement_eur_user":str(C+alpha*Az),
                 "user_share_of_zk_pool_eur_user":str(user_pool),
                 "service_subsidy_eur_user":str(R),"service_subsidy_eur_population":str(R*cfg["population_n"]),
                 "service_subsidy_eur_deposit":str(R/n),
                 "user_network_difference_vs_B0_eur_user":str(user_delta),
                 "user_pool_difference_vs_B0_eur_user":str(user_delta),
                 "network_extra_resource_cost_zk_vs_signed_eur_user":str(Az-As),
                 "alpha_crit_user_network_indifference":str(crit),
                 "gas_only_user_not_more_expensive_than_B0":str(alpha<=crit),
                 "incremental_service_coverage_needed_vs_B0_eur_user_if_other_terms_match":str(R),
                 "minimum_m_required_expression":f"m_ZK >= s_ZK_other + {R} EUR - f + F_ZK/{cfg['population_n']}",
                 "incremental_m_required_vs_B0_expression":f"(m_ZK-m_B0) >= (s_ZK_other-s_B0_other) + {R} EUR + (F_ZK-F_B0)/{cfg['population_n']} (for equal fee f)",
                 "required_user_benefit_expression":f"B_required = {user_delta} EUR + (u_ZK_other-u_B0_other) + v*(t_ZK-t_B0)",
                 "gas_cost_conservation_error_eur_user":str((C+alpha*Az+R)-(C+Az)),
                 "unresolved_items":"u_other, s_other, f, m_ZK/m_B0, F_ZK/F_B0, v, active user time, payout overhead and cash equivalence are unknown",
                 "cash_compensation_status":"NOT IMPLEMENTED; conditional hypothetical cash-equivalent reimbursement"
                }
                out.append(row)
    assert len(out)==30 and len(baselines)==6
    hashes={f:digest(input_dir/f) for f in INPUT_NAMES}
    meta={"researcher":"Nataliya Kolyada","stage":"ECON-05 reproducible core sweep v0.1 — submitted for review", "technical_owner_and_reviewer":"Oleksandr Kuznetsov", "source_commit_identifiers_supplied_by_technical_owner":PINNED,"reuse":"economic_model.py is byte-identical to accepted ECON-04 v0.1 implementation", "input_file_sha256":hashes,"config_sha256":digest(config_path),"fee_scenarios":"archived p50/p90 gwei prices, not daily/90d invoice quantiles", "row_count":len(out),"distinct_economic_cases":15,"pricing_cases":2,"context":{k:cfg[k] for k in ("horizon_days","policy","services","population_n","issuers","credential_days","auth_ttl_days","deposit_counts","user_shares","price_scenarios")},"scope":"synthetic frequency projections repriced; no changes to cryptography, proof generation, temporal path or future extension", "warning":"No profit, demand, WTP, live subsidy, tested payout overhead or observed user behavior is inferred.","unresolved":"u_other, s_other, f, m, F, v, timing, cash payout overhead/implementation and liquidity requirements","ai_assistance":"AI-assisted code, tables, visualizations, drafting; externally supplied gas measurement data are not remeasured; requires independent review"}
    return out,baselines,meta


def save():
    records,base,meta=produce_sweep()
    out=BASE/"results";out.mkdir(exist_ok=True)
    for file,sequence in [("econ05_sweep_30rows.csv",records),("b0_reference_6rows.csv",base)]:
        with (out/file).open("w",encoding="utf-8",newline="") as fp:
            w=csv.DictWriter(fp,fieldnames=(FIELDS if file.startswith("econ05_") else list(sequence[0])));w.writeheader();w.writerows(sequence)
    (out/"run_metadata.json").write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding="utf-8")
    for n in [1,10,100]:
        for price in ["p50","p90"]:
            r=next(t for t in records if int(t["activity_deposits_per_user_90d"])==n and t["fee_scenario"]==price and t["user_share_alpha"]=="0.5")
            print(f"n={n:3d} {price}: signed {r['baseline_signed_variant']:<12}, ZK {r['selected_zk_variant']:<10} A_ZK={D(r['zk_access_pool_eur_user']):.6f} EUR, B2 subsidy@alpha=.5={D(r['service_subsidy_eur_user']):.6f} EUR, alpha*={D(r['alpha_crit_user_network_indifference']):.4%}")
    print("Output: 30 pricing rows for 15 cases; accepted prior ECON-04 selector and event validation reused")

if __name__=="__main__": save()
