#!/usr/bin/env python3
"""State-trace accounting for the measured v2 access architectures.

The primary grid has 96 workload contexts, not thousands of independent
experiments. Four architectures and available local chains are evaluated on
each context. Assumed execution prices are a separate conversion table.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_CEILING
from fractions import Fraction
from pathlib import Path
from typing import Any


VARIANTS = ("signed_direct", "signed_cache", "zk_direct", "zk_cache")
CHURN_MODES = ("none", "weekly", "daily", "population_unbatched")
PRICE_LEVELS = tuple(Decimal(x) for x in ("0.05", "0.4", "1", "10"))
SHARED_DEPLOYMENTS = ("deploy_poseidon", "deploy_registry", "deploy_token", "issuer_root_initial")


def dec(value: int | Fraction | Decimal | float) -> Decimal:
    if isinstance(value, Fraction):
        return Decimal(value.numerator) / Decimal(value.denominator)
    return Decimal(str(value))


def cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (Decimal, Fraction)):
        text = format(dec(value), "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    return value


def quantile(values: list[Decimal], probability: Decimal) -> Decimal:
    """Linear interpolation on sorted observations (R-7 / common default)."""
    ordered = sorted(values)
    index = probability * (len(ordered) - 1)
    low = int(index)
    if low == len(ordered) - 1:
        return ordered[low]
    return ordered[low] + (index - low) * (ordered[low + 1] - ordered[low])


def summarise_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("schema_version") != 2:
        raise ValueError("measurements schema_version must be 2")
    records = payload.get("events")
    if not isinstance(records, list) or not records:
        raise ValueError("a nonempty measured events list is required")
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        if row.get("chain") not in {"l1", "op"}:
            raise ValueError("chain must be l1 or op")
        if row.get("variant") not in {*VARIANTS, "shared"}:
            raise ValueError("unknown architecture variant")
        if row.get("evidence_status") != "measured_local":
            raise ValueError("unmeasured input cannot enter measured-event accounting")
        if not isinstance(row.get("event"), str) or not row["event"]:
            raise ValueError("each record requires an event name")
        if not isinstance(row.get("scope"), str) or not row["scope"]:
            raise ValueError("each record requires an explicit scope")
        for metric in ("gas_used", "proof_time_ms"):
            value = row.get(metric)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{metric} must be finite and nonnegative, or null")
            if metric == "gas_used" and int(value) != value:
                raise ValueError("receipt gas_used must be an integer")
        groups[(row["chain"], row["variant"], row["event"])].append(row)

    result = []
    for (chain, variant, event), observations in sorted(groups.items()):
        scopes = {row["scope"] for row in observations}
        if len(scopes) != 1:
            raise ValueError(f"conflicting scopes for {chain}/{variant}/{event}")
        for metric, unit in (("gas_used", "gas"), ("proof_time_ms", "ms")):
            values = [dec(row[metric]) for row in observations if row.get(metric) is not None]
            if not values:
                continue
            q1, q3 = quantile(values, Decimal("0.25")), quantile(values, Decimal("0.75"))
            result.append({
                "chain": chain, "variant": variant, "event": event,
                "scope": observations[0]["scope"], "metric": metric, "unit": unit,
                "mean": sum(values) / len(values), "min": min(values), "median": quantile(values, Decimal("0.5")),
                "q1": q1, "q3": q3, "iqr": q3 - q1, "max": max(values),
                "sum_observed": sum(values), "n": len(values), "n_event_records": len(observations),
                "sample_interpretation": "single_observation" if len(values) == 1 else "local_repeated_observations_not_population_uncertainty",
                "evidence_status": "measured_local",
                "source_runs": ";".join(str(row.get("run", "")) for row in observations if row.get(metric) is not None),
                "source_tx_hashes": ";".join(str(row.get("tx_hash", "")) for row in observations if row.get(metric) is not None),
            })
    return result


class Measurements:
    def __init__(self, summaries: list[dict[str, Any]]):
        self.summaries = summaries
        self.index = {(r["chain"], r["variant"], r["event"], r["metric"]): r for r in summaries}
        self.chains = sorted({row["chain"] for row in summaries})

    def gas(self, chain: str, variant: str, event: str, *, total_observed: bool = False) -> Decimal:
        row = self.index.get((chain, variant, event, "gas_used"))
        if row is None and variant != "shared":
            row = self.index.get((chain, "shared", event, "gas_used"))
        if row is None or row["n"] != row["n_event_records"]:
            raise ValueError(f"missing/incomplete measured gas: {chain}/{variant}/{event}")
        return row["sum_observed" if total_observed else "mean"]

    def warm_proof(self, chain: str) -> tuple[Decimal | None, int]:
        # Same circuit: pool actual warm observations, weighted by sample count.
        # First-process/first-holder timing is retained in raw summaries only.
        rows = []
        for variant, event in (("zk_direct", "access_repeat"), ("zk_cache", "cache_reauthorize")):
            row = self.index.get((chain, variant, event, "proof_time_ms"))
            if row is None or row["n"] != row["n_event_records"]:
                return None, sum(r["n"] for r in rows)
            rows.append(row)
        count = sum(row["n"] for row in rows)
        return sum(row["sum_observed"] for row in rows) / count, count


@dataclass(frozen=True)
class Context:
    n_accesses: int
    apps_deployed: int
    population: int
    validity_days: int
    root_churn: str
    horizon_days: int = 90
    auth_ttl_days: int = 30

    def validate(self) -> None:
        if any(value <= 0 for value in (self.n_accesses, self.apps_deployed, self.population, self.validity_days, self.horizon_days, self.auth_ttl_days)):
            raise ValueError("positive workload, population, validity, horizon and authorization TTL required")
        if self.root_churn not in CHURN_MODES:
            raise ValueError("unknown root-churn regime")

    @property
    def context_id(self) -> str:
        return f"n{self.n_accesses}-K{self.apps_deployed}-N{self.population}-L{self.validity_days}-{self.root_churn}"


def contexts(auth_ttl_days: int = 30) -> list[Context]:
    return [Context(n, k, population, lifetime, churn, auth_ttl_days=auth_ttl_days)
            for n, k, population, lifetime, churn in itertools.product((1, 10, 100), (1, 5), (10, 1000), (30, 90), CHURN_MODES)]


def trace(context: Context) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Representative new-user trace in a stated common mixed registry.

    Population members use the same relative access/renewal schedule; visits
    may be rotated across apps. Renewal publications are unbatched N updates
    at each shared renewal timestamp, processed before accesses at that time.
    This synchronized synthetic population is a conditional scenario, not an
    empirical population model. Background changes preserve this user's
    eligibility; no denial/failure demand is inserted.
    """
    context.validate()
    T, n, N = context.horizon_days, context.n_accesses, context.population
    times = [Fraction(T * i, n) for i in range(n)]
    expiry = Fraction(context.validity_days)
    renewal_times = []
    expiry_at_access = []
    for timestamp in times:
        if timestamp >= expiry:
            renewal_times.append(timestamp)
            expiry = timestamp + context.validity_days
        expiry_at_access.append(expiry)

    if context.root_churn == "none":
        background = []
    elif context.root_churn in {"weekly", "daily"}:
        period = 7 if context.root_churn == "weekly" else 1
        background = [Fraction(day) for day in range(period, T, period)]
    else:
        # One unrelated eligibility-preserving update per population member,
        # evenly distributed and unbatched, all strictly within [0,T).
        background = [Fraction(T * (2 * i + 1), 2 * N) for i in range(N)]
    root_updates = Counter(background)
    for timestamp in renewal_times:
        root_updates[timestamp] += N
    update_times = sorted(root_updates)
    cumulative = [0]
    for timestamp in update_times:
        cumulative.append(cumulative[-1] + root_updates[timestamp])

    caches: dict[int, tuple[int, Fraction]] = {}
    counts: Counter[str] = Counter()
    rows = []
    for i, timestamp in enumerate(times):
        app = i % context.apps_deployed
        epoch = cumulative[bisect.bisect_right(update_times, timestamp)]
        credential_expiry = expiry_at_access[i]
        prior = caches.get(app)
        reason = ""
        prior_epoch = prior[0] if prior else None
        prior_until = prior[1] if prior else None
        if prior is None:
            cache_event = "cache_register_first"
            direct_event = "access_first"
            counts["approve"] += 1
        else:
            direct_event = "access_repeat"
            stale = prior[0] != epoch
            expired = timestamp >= prior[1]
            if stale or expired:
                cache_event = "cache_reauthorize"
                reason = "root_and_expiry" if stale and expired else "root" if stale else "expiry"
                counts[f"reauth_{reason}"] += 1
            else:
                cache_event = "cache_hit"
                if not (prior[0] == epoch and timestamp < prior[1]):
                    raise AssertionError("a cache hit must be current and unexpired")
        counts[direct_event] += 1
        counts[cache_event] += 1
        if cache_event != "cache_hit":
            caches[app] = (epoch, min(timestamp + context.auth_ttl_days, credential_expiry))
        rows.append({
            "context_id": context.context_id, "access_index": i,
            "timestamp_days": timestamp, "timestamp_exact": str(timestamp), "app_index": app,
            "registry_epoch_delta": epoch, "credential_expiry_days": credential_expiry,
            "credential_refresh_at_this_time": timestamp in renewal_times,
            "prior_cache_epoch_delta": prior_epoch, "prior_cache_until_days": prior_until,
            "direct_event": direct_event, "cache_event": cache_event, "cache_miss_reason": reason,
            "cache_until_after_days": caches[app][1],
        })
    stats = {
        "context_id": context.context_id, **asdict(context),
        "apps_visited_per_user": min(context.apps_deployed, n),
        "credential_issues_per_user": 1,
        "credential_refreshes_per_user": len(renewal_times),
        "root_publications_background": len(background),
        "root_publications_refresh_population": N * len(renewal_times),
        "root_publications_total": len(background) + N * len(renewal_times),
        **{key: counts[key] for key in ("approve", "access_first", "access_repeat", "cache_register_first", "cache_hit", "cache_reauthorize", "reauth_root", "reauth_expiry", "reauth_root_and_expiry")},
        "root_churn_interpretation": "one_background_change_per_person_per_horizon_unbatched" if context.root_churn == "population_unbatched" else "exogenous_schedule_independent_of_population",
        "renewal_root_model": "common_mixed_registry; synchronized_new_user_traces; unbatched_N_publications_per_renewal_timestamp",
        "tie_order": "root_updates_and_credential_refresh_before_access",
        "failure_events": 0,
        "population_status": "assumed_scenario_not_observed_population",
    }
    assert stats["access_first"] + stats["access_repeat"] == n
    assert stats["cache_register_first"] + stats["cache_hit"] + stats["cache_reauthorize"] == n
    assert stats["credential_issues_per_user"] == 1
    return stats, rows


def charge_terms(family: str, refreshes: int) -> str:
    return f"1 * p_{family}_initial_issuance" + (f" + {refreshes} * p_{family}_credential_refresh" if refreshes else "")


def evaluate(measurements: Measurements, context: Context, stats: dict[str, Any], chain: str, variant: str) -> dict[str, Any]:
    cached, zk = variant.endswith("_cache"), variant.startswith("zk_")
    family = "zk" if zk else "signed"
    event_counts = {"approve": stats["approve"]}
    event_counts.update({key: stats[key] for key in (("cache_register_first", "cache_hit", "cache_reauthorize") if cached else ("access_first", "access_repeat"))})
    user_gas = sum(count * measurements.gas(chain, variant, event) for event, count in event_counts.items() if count)
    # Fixed registry setup is counted once, not once per user. Initial root
    # records are distinct initialization transactions, not repeat samples.
    common_setup = sum(measurements.gas(chain, "shared", event, total_observed=True) for event in SHARED_DEPLOYMENTS)
    verifier_setup = measurements.gas(chain, "shared", "deploy_verifier", total_observed=True) if zk else Decimal(0)
    app_setup = context.apps_deployed * measurements.gas(chain, variant, "deploy_gate")
    bootstrap_setup = context.apps_deployed * measurements.gas(chain, variant, "bootstrap_token_balance")
    fixed = common_setup + verifier_setup + app_setup + bootstrap_setup
    update_gas = stats["root_publications_total"] * measurements.gas(chain, "shared", "issuer_root_update") if stats["root_publications_total"] else Decimal(0)
    proof_mean, proof_n = measurements.warm_proof(chain)
    proof_count = (stats["cache_register_first"] + stats["cache_reauthorize"] if cached else context.n_accesses) if zk else 0
    proof_total = Decimal(0) if not zk else None if proof_mean is None else proof_count * proof_mean
    return {
        "context_id": context.context_id, "chain": chain, "variant": variant,
        "n_accesses": context.n_accesses, "apps_deployed": context.apps_deployed,
        "apps_visited_per_user": stats["apps_visited_per_user"], "population": context.population,
        "horizon_days": context.horizon_days, "validity_days": context.validity_days,
        "auth_ttl_days": context.auth_ttl_days, "root_churn": context.root_churn,
        "credential_issues_per_user": 1, "credential_refreshes_per_user": stats["credential_refreshes_per_user"],
        "root_publications_background": stats["root_publications_background"],
        "root_publications_refresh_population": stats["root_publications_refresh_population"],
        "root_publications_total": stats["root_publications_total"],
        "approve_count": stats["approve"],
        "full_authorizations_per_user": stats["cache_register_first"] + stats["cache_reauthorize"] if cached else context.n_accesses,
        "cache_hits_per_user": stats["cache_hit"] if cached else 0,
        "cache_reauthorizations_per_user": stats["cache_reauthorize"] if cached else 0,
        "user_action_gas_per_user": user_gas,
        "common_demo_setup_gas_once": common_setup,
        "verifier_setup_gas_once": verifier_setup,
        "app_deployment_gas_once": app_setup,
        "fixture_bootstrap_gas_once": bootstrap_setup,
        "all_demo_setup_gas_once": fixed,
        "registry_update_gas_population": update_gas,
        "demo_setup_gas_per_user": fixed / context.population,
        "registry_update_gas_per_user": update_gas / context.population,
        "known_execution_gas_per_user": user_gas + (fixed + update_gas) / context.population,
        "proofs_per_user": proof_count,
        "warm_proof_ms_per_proof": proof_mean if zk else None,
        "warm_proof_sample_count": proof_n if zk else 0,
        "derived_prover_ms_per_user": proof_total,
        "prover_time_status": "not_applicable_no_ZK" if not zk else "missing_warm_measurement" if proof_mean is None else "pooled_warm_local_work_not_end_to_end_latency",
        "unknown_issuer_charge_expression": charge_terms(family, stats["credential_refreshes_per_user"]),
        "fee_boundary": "execution_only_excludes_L1_data_and_operator_fees" if chain == "op" else "local_EVM_execution_fee_projection",
        "total_cost_status": "not_computed_unknown_tariffs_other_costs_and_possible_invoice_overlap",
        "comparison_boundary": "common_mixed_registry_not_minimal_standalone_signed_system",
        "setup_boundary": "full_demo_including_mock_token_and_bootstrap; components_separate",
        "derivation_status": "state_trace_projection_not_an_executed_population_benchmark",
    }


def break_even(measurements: Measurements, context: Context, stats: dict[str, Any], chain: str, family: str, direct: dict[str, Any], cached: dict[str, Any]) -> dict[str, Any]:
    variant = family + "_cache"
    first = stats["cache_register_first"]
    cached_no_reauth = (
        stats["approve"] * measurements.gas(chain, variant, "approve")
        + first * measurements.gas(chain, variant, "cache_register_first")
        + (context.n_accesses - first) * measurements.gas(chain, variant, "cache_hit")
    )
    fixed_premium = cached["all_demo_setup_gas_once"] - direct["all_demo_setup_gas_once"]
    headroom = direct["user_action_gas_per_user"] - cached_no_reauth - fixed_premium / context.population
    reauth_premium = measurements.gas(chain, variant, "cache_reauthorize") - measurements.gas(chain, variant, "cache_hit")
    real_threshold = headroom / reauth_premium if reauth_premium > 0 else None
    if real_threshold is not None and headroom > 0:
        maximum = min(context.n_accesses - first, max(0, int(real_threshold.to_integral_value(rounding=ROUND_CEILING)) - 1))
    else:
        maximum = None
    saving = direct["known_execution_gas_per_user"] - cached["known_execution_gas_per_user"]
    reconstructed = headroom - stats["cache_reauthorize"] * reauth_premium
    if abs(saving - reconstructed) > Decimal("1e-18"):
        raise AssertionError("cache break-even decomposition does not reconcile")
    return {
        "context_id": context.context_id, "chain": chain, "family": family,
        "n_accesses": context.n_accesses, "apps_visited_per_user": stats["apps_visited_per_user"],
        "population": context.population, "root_churn": context.root_churn,
        "actual_reauthorizations": stats["cache_reauthorize"], "actual_cache_hits": stats["cache_hit"],
        "headroom_before_reauthorizations_gas_per_user": headroom,
        "additional_gas_per_reauthorization": reauth_premium,
        "reauthorizations_strict_break_even_real": real_threshold,
        "max_reauthorizations_for_strict_saving": maximum,
        "threshold_status": "no_strict_saving_even_at_zero_reauthorizations" if headroom <= 0 else "conditional_fixed_workload_threshold" if reauth_premium > 0 else "nonpositive_reauthorization_premium_inspect_measurements",
        "direct_known_gas_per_user": direct["known_execution_gas_per_user"],
        "cached_known_gas_per_user": cached["known_execution_gas_per_user"],
        "cached_gas_saving_per_user": saving,
        "cache_saves_gas_this_trace": saving > 0,
        "test": "actual_reauthorizations * additional_gas_per_reauthorization < headroom_before_reauthorizations",
        "scope": "gas_only_fixed_trace; unknown_differential_offchain_charges_not_assumed_zero",
    }


def price_inputs() -> list[dict[str, str]]:
    rows = []
    for family, operation in itertools.product(("signed", "zk"), ("initial_issuance", "credential_refresh")):
        rows.append({
            "price_id": f"p_{family}_{operation}", "value": "", "currency": "UNSPECIFIED", "unit": "per_event",
            "evidence_status": "unknown", "source": "",
            "accounting_note": "Before adding any quote, determine whether it includes already-counted root-publication gas. Issuer invoices may be internal transfers under a mixed-system boundary.",
        })
    for key, currency, unit, note in (
        ("ETH_EUR", "EUR", "per_ETH", "No current exchange rate is invented."),
        ("prover_service", "UNSPECIFIED", "per_proof", "CPU milliseconds alone are not an invoice."),
        ("op_L1_data_fee", "ETH", "per_transaction", "Missing OP data fee is not zero; execution component only is reported."),
        ("op_operator_fee", "ETH", "per_transaction", "Missing operator fee is not zero; execution component only is reported."),
    ):
        rows.append({"price_id": key, "value": "", "currency": currency, "unit": unit, "evidence_status": "unknown", "source": "", "accounting_note": note})
    return rows


def price_sensitivity(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for result, price in itertools.product(results, PRICE_LEVELS):
        conversion = price * Decimal("1e-9")
        rows.append({
            "context_id": result["context_id"], "chain": result["chain"], "variant": result["variant"],
            "assumed_effective_execution_price_gwei": price,
            "user_action_execution_eth_per_user": result["user_action_gas_per_user"] * conversion,
            "demo_setup_execution_eth_per_user": result["demo_setup_gas_per_user"] * conversion,
            "registry_update_execution_eth_per_user": result["registry_update_gas_per_user"] * conversion,
            "known_execution_eth_per_user": result["known_execution_gas_per_user"] * conversion,
            "price_status": "assumed_stress_level_not_a_market_quote",
            "fee_boundary": result["fee_boundary"], "total_cost_status": result["total_cost_status"],
            "interpretation": "unit_price_postprocessing_not_an_independent_implementation_experiment",
        })
    return rows


def observed_fee_projection(results: list[dict[str, Any]], source: Path) -> list[dict[str, Any]]:
    """Convert measured gas with block-weighted observed fee proxies.

    These are p10/p50/p90 across blocks' own effective p50 fee, not pooled
    transaction quantiles or execution outcomes of these demo transactions.
    """
    raw = source.read_bytes()
    snapshot = json.loads(raw)
    if snapshot.get("status") != "available":
        raise ValueError("fee snapshot is not available; no observed price may be imputed")
    networks = {row["network"]: row for row in snapshot["networks"]}
    archive = snapshot.get("raw_archive", {})
    archive_hash = archive.get("sha256")
    if not isinstance(archive_hash, str) or len(archive_hash) != 64:
        raise ValueError("fee snapshot requires its raw archive SHA256")
    rows = []
    for result in results:
        network = {"l1": "ethereum", "op": "optimism"}[result["chain"]]
        observed = networks.get(network)
        if not observed or observed.get("status") != "available":
            raise ValueError(f"missing observed fee summary for {network}; do not substitute another chain")
        summary = observed["summary"]["within_block_effective_p50_block_weighted"]
        window = observed["window"]
        for percentile in (10, 50, 90):
            price = Decimal(str(summary[f"p{percentile}_wei"]))
            if not price.is_finite() or price < 0 or int(price) != price:
                raise ValueError("observed execution fee must be a nonnegative integer wei amount")
            conversion = price * Decimal("1e-18")
            rows.append({
                "context_id": result["context_id"], "chain": result["chain"], "variant": result["variant"],
                "network": network, "block_distribution_percentile": percentile,
                "observed_execution_price_proxy_wei": price,
                "observed_execution_price_proxy_gwei": price * Decimal("1e-9"),
                "user_action_execution_eth_per_user": result["user_action_gas_per_user"] * conversion,
                "demo_setup_execution_eth_per_user": result["demo_setup_gas_per_user"] * conversion,
                "registry_update_execution_eth_per_user": result["registry_update_gas_per_user"] * conversion,
                "known_execution_eth_per_user": result["known_execution_gas_per_user"] * conversion,
                "price_status": "observed_network_fee_proxy_applied_to_local_measured_gas",
                "price_metric": "nearest_rank_block_weighted_percentile_of_within_block_effective_p50; not_global_transaction_quantile",
                "fee_boundary": result["fee_boundary"], "total_cost_status": result["total_cost_status"],
                "window_first_block": window["first_block"]["number"],
                "window_last_block": window["last_block"]["number"],
                "window_start_utc": window["first_block"]["timestamp_utc"],
                "window_end_utc": window["last_block"]["timestamp_utc"],
                "window_boundary_span_seconds": window["boundary_timestamp_span_seconds"],
                "window_block_count": window["block_count"], "price_observations": summary["observations"],
                "fee_source_url": observed["source_url"],
                "fee_snapshot_source": str(source), "fee_snapshot_sha256": hashlib.sha256(raw).hexdigest(),
                "raw_fee_archive_path": archive.get("path", ""), "raw_fee_archive_sha256": archive_hash,
                "interpretation": "historical_proxy_conversion_not_measured_mainnet_transaction_cost; different_chain_windows_not_time_matched",
            })
    return rows


def allocation_rules() -> list[dict[str, Any]]:
    """Keep payer incidence separate from resource costs and observations."""
    return [{
        "user_share_alpha": alpha, "sponsor_share": 1 - alpha,
        "user_cash_formula": "alpha * selected_known_execution_eth_per_user",
        "sponsor_cash_formula": "(1-alpha) * selected_known_execution_eth_per_user",
        "cost_pool": "known_execution_budget_only; unknown_issuer_prover_and_OP_other_fees_excluded",
        "interpretation": "accounting_transfer_rule_not_gas_savings_or_independent_experiment; actual_transaction_sender_is_unchanged_without_subsidy_mechanism",
        "behavioral_status": "no_revenue_demand_or_willingness_to_pay_inferred",
    } for alpha in map(Decimal, ("0", ".25", ".5", ".75", "1"))]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write an empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({key: cell(value) for key, value in row.items()} for row in rows)


def export(source: Path, out: Path, *, auth_ttl_days: int = 30, fee_snapshot: Path | None = None) -> dict[str, Any]:
    raw = source.read_bytes()
    payload = json.loads(raw)
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    summaries = summarise_events(payload)
    measurements = Measurements(summaries)
    trace_counts, trace_rows, results, comparisons = [], [], [], []
    for context in contexts(auth_ttl_days):
        stats, events = trace(context)
        trace_counts.append(stats)
        trace_rows.extend(events)
        for chain in measurements.chains:
            group = {variant: evaluate(measurements, context, stats, chain, variant) for variant in VARIANTS}
            results.extend(group.values())
            for family in ("signed", "zk"):
                comparisons.append(break_even(measurements, context, stats, chain, family, group[family + "_direct"], group[family + "_cache"]))
    provenance = {
        "source_sha": metadata.get("source_sha", metadata.get("source_commit", "unknown")),
        "source_tree_sha256": metadata.get("source_tree_sha256", "unknown"),
        "source_dirty": metadata.get("source_dirty", "unknown"),
        "measurements_sha256": hashlib.sha256(raw).hexdigest(),
        "economics_exporter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "measurement_source": str(source),
    }
    tables = {
        "event_measurements.csv": summaries,
        "trace_counts.csv": trace_counts,
        "trace_events.csv": trace_rows,
        "architecture_results.csv": results,
        "break_even.csv": comparisons,
        "price_sensitivity.csv": price_sensitivity(results),
        "allocation_rules.csv": allocation_rules(),
    }
    observed_source = fee_snapshot if fee_snapshot is not None else source.parent / "fee_snapshot.json"
    if fee_snapshot is not None or observed_source.exists():
        tables["observed_fee_projection.csv"] = observed_fee_projection(results, observed_source)
    # All calculations/required measurements are validated before any write.
    out.mkdir(parents=True, exist_ok=True)
    for filename, rows in tables.items():
        write_csv(out / filename, [dict(row, **provenance) for row in rows])
    write_csv(out / "price_inputs.csv", price_inputs())
    return {"workload_contexts": len(trace_counts), "architecture_chain_results": len(results), "chains": measurements.chains, "trace_access_rows": len(trace_rows), "price_rows_are_postprocessing": len(tables["price_sensitivity.csv"]), "observed_fee_projection_rows": len(tables.get("observed_fee_projection.csv", [])), "observed_fee_status": "available" if "observed_fee_projection.csv" in tables else "not_supplied_no_prices_imputed", "allocation_rules": 5, "output_directory": str(out)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--auth-ttl-days", type=int, default=30)
    parser.add_argument("--fee-snapshot", type=Path, help="Optional archived fee summary; defaults to fee_snapshot.json beside measurements when present.")
    args = parser.parse_args()
    try:
        result = export(args.measurements, args.out, auth_ttl_days=args.auth_ttl_days, fee_snapshot=args.fee_snapshot)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"v2 economics export failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
