#!/usr/bin/env python3
"""Export measured local event inputs and a conditional access-cost grid.

Only transaction gas is priced numerically. Issuer prices, other operating
costs and ETH/EUR conversion are deliberately unknown. No result is a complete
service-cost, profit, demand or mainnet-latency estimate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any


HORIZON_DAYS = 90
WORKLOADS = (1, 10, 100)
VALIDITIES = (30, 90, 365)
USER_SHARES = tuple(Decimal(x) for x in ("0", "0.25", "0.5", "0.75", "1"))
GAS_PRICES_GWEI = (1, 10, 100)
METRICS = {"gas_used": "gas", "proof_time_ms": "ms", "offchain_verify_ms": "ms"}


def number(value: Decimal | Fraction | int | float | None) -> str:
    """Write finite numeric values without implicit NaN-to-zero conversion."""
    if value is None:
        return ""
    if isinstance(value, Fraction):
        value = Decimal(value.numerator) / Decimal(value.denominator)
    result = format(Decimal(str(value)), "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


def renewal_count(
    n_accesses: int,
    validity_days: int,
    *,
    cohort: str,
    horizon_days: int = HORIZON_DAYS,
) -> int:
    """Refresh on first use at/after expiry; new expiry = refresh time + L.

    Accesses are at T*i/n, i=0,...,n-1. The returning user's remaining
    validity is L/2, a stated scenario assumption, not a population estimate.
    Exact rational times avoid floating-point expiry-boundary errors.
    """
    if n_accesses < 1 or validity_days <= 0 or horizon_days <= 0:
        raise ValueError("workload, validity and horizon must be positive")
    if cohort not in {"new", "returning"}:
        raise ValueError("cohort must be new or returning")
    expiry = Fraction(validity_days, 1 if cohort == "new" else 2)
    refreshes = 0
    for i in range(n_accesses):
        timestamp = Fraction(horizon_days * i, n_accesses)
        if timestamp >= expiry:
            refreshes += 1
            expiry = timestamp + validity_days
    return refreshes


def summarise_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("schema_version") != 1:
        raise ValueError("measurements schema_version must be 1")
    events = payload.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("measurements must contain a non-empty events list")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        if event.get("variant") not in {"baseline", "zk", "shared"}:
            raise ValueError(f"unsupported event variant: {event.get('variant')!r}")
        if not isinstance(event.get("event"), str) or not event["event"]:
            raise ValueError("every measurement needs an event name")
        if event.get("evidence_status") != "measured_local":
            raise ValueError("only measured_local events may enter this exporter")
        if event.get("scope") not in {"per_action", "per_credential", "shared_fixed"}:
            raise ValueError(f"unsupported measurement scope: {event.get('scope')!r}")
        for metric in METRICS:
            value = event.get(metric)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{metric} must be numeric or null")
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{metric} must be finite and non-negative")
            if metric == "gas_used" and int(value) != value:
                raise ValueError("receipt gas_used must be an integer")
        grouped[(event["variant"], event["event"])].append(event)

    rows = []
    for (variant, event_name), records in sorted(grouped.items()):
        scopes = {event["scope"] for event in records}
        if len(scopes) != 1:
            raise ValueError(f"conflicting scopes for {variant}/{event_name}")
        for metric, unit in METRICS.items():
            values = [Decimal(str(event[metric])) for event in records if event.get(metric) is not None]
            if not values:
                continue
            rows.append({
                "variant": variant,
                "event": event_name,
                "scope": records[0]["scope"],
                "metric": metric,
                "unit": unit,
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "n": len(values),
                "n_event_records": len(records),
                "evidence_status": "measured_local",
                "source_runs": ";".join(str(event.get("run", "")) for event in records if event.get(metric) is not None),
                "source_tx_hashes": ";".join(str(event.get("tx_hash", "")) for event in records if event.get(metric) is not None),
            })
    return rows


def event_metric(
    summaries: list[dict[str, Any]], variant: str, event: str, metric: str,
    *, required: bool = False,
) -> Decimal | None:
    # A measured shared token approval can be used by either gate.
    matches = [row for row in summaries if row["variant"] == variant and row["event"] == event and row["metric"] == metric]
    if not matches:
        matches = [row for row in summaries if row["variant"] == "shared" and row["event"] == event and row["metric"] == metric]
    if len(matches) > 1:
        raise ValueError(f"ambiguous metric: {variant}/{event}/{metric}")
    if not matches:
        if required:
            raise ValueError(f"missing measured metric: {variant}/{event}/{metric}")
        return None
    if matches[0]["scope"] == "shared_fixed":
        raise ValueError(f"a shared fixed event cannot be counted per user: {variant}/{event}")
    return matches[0]["mean"]


def event_sum(
    summaries: list[dict[str, Any]], variant: str, counts: dict[str, int],
    metric: str, *, required: bool = False,
) -> Decimal | None:
    result = Decimal(0)
    for event, count in counts.items():
        if count == 0:
            continue
        value = event_metric(summaries, variant, event, metric, required=required)
        if value is None:
            return None
        result += count * value
    return result


def pooled_deposit_timing(summaries: list[dict[str, Any]], metric: str) -> tuple[Decimal | None, int]:
    """Pool successful proof timings; process warmup is not a cohort effect.

    First/repeat raw statistics stay in event_measurements.csv. All successful
    proof observations must be present to avoid concealing partial timing data.
    """
    timing_rows = []
    for event in ("deposit_first", "deposit_repeat"):
        measured = [row for row in summaries if row["variant"] == "zk" and row["event"] == event and row["metric"] == metric]
        if len(measured) != 1 or measured[0]["n"] != measured[0]["n_event_records"]:
            return None, sum(row["n"] for row in timing_rows)
        timing_rows.extend(measured)
    count = sum(row["n"] for row in timing_rows)
    return sum(row["mean"] * row["n"] for row in timing_rows) / count, count


def issuer_terms(variant: str, issue_count: int, refresh_count: int, share: Decimal = Decimal(1)) -> str:
    terms = []
    for count, suffix in ((issue_count, "initial_issuance"), (refresh_count, "credential_refresh")):
        coefficient = Decimal(count) * share
        if coefficient:
            terms.append(f"{number(coefficient)} * {variant}_{suffix}")
    return " + ".join(terms) or "0"


def build_scenarios(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    pooled_proof_ms, proof_samples = pooled_deposit_timing(summaries, "proof_time_ms")
    pooled_verify_ms, _ = pooled_deposit_timing(summaries, "offchain_verify_ms")
    for cohort, n, alpha, gas_price, validity in itertools.product(
        ("new", "returning"), WORKLOADS, USER_SHARES, GAS_PRICES_GWEI, VALIDITIES,
    ):
        issue_count = int(cohort == "new")
        counts = {
            "approve": issue_count,
            "deposit_first": issue_count,
            "deposit_repeat": n - issue_count,
        }
        refreshes = renewal_count(n, validity, cohort=cohort)
        b0_gas = event_sum(summaries, "baseline", counts, "gas_used", required=True)
        b1_gas = event_sum(summaries, "zk", counts, "gas_used", required=True)
        assert b0_gas is not None and b1_gas is not None
        proof_ms = None if pooled_proof_ms is None else n * pooled_proof_ms
        verify_ms = None if pooled_verify_ms is None else n * pooled_verify_ms
        price_eth = Decimal(gas_price) * Decimal("0.000000001")
        b0_cost, b1_cost = b0_gas * price_eth, b1_gas * price_eth
        rows.append({
            "scenario_id": f"{cohort}-n{n}-a{number(alpha)}-g{gas_price}-L{validity}",
            "cohort": cohort,
            "horizon_days": HORIZON_DAYS,
            "validity_days": validity,
            "remaining_validity_days": Fraction(validity, 1 if cohort == "new" else 2),
            "n_accesses": n,
            "alpha_user": alpha,
            "gas_price_gwei": gas_price,
            "gas_price_status": "assumed_effective_price_not_current_market_quote",
            "credential_timing_status": "assumed_not_compliance_recommendation",
            "approve_count": counts["approve"],
            "deposit_first_count": counts["deposit_first"],
            "deposit_repeat_count": counts["deposit_repeat"],
            "b0_issue_count": issue_count,
            "b0_refresh_count": refreshes,
            "b1_issue_count": issue_count,
            "b1_refresh_count": refreshes,
            "renewal_onchain_tx_count": 0,
            "revocation_event_count": 0,
            "revocation_assumption": "no_revocation_events_in_this_projection; per_access_status_check_is_in_deposit_gas",
            "b0_gas_total": b0_gas,
            "b1_gas_total": b1_gas,
            "b1_prover_ms_per_access": pooled_proof_ms,
            "b1_prover_samples": proof_samples,
            "b1_prover_ms_total": proof_ms,
            "b1_offchain_verify_ms_total": verify_ms,
            "prover_time_status": "derived_from_local_measurements" if proof_ms is not None else "missing_measurement",
            "prover_time_model": "sample_weighted_successful_proofs; process_warmup_is_not_a_cohort_effect",
            "b0_chain_cost_eth": b0_cost,
            "b1_chain_cost_eth": b1_cost,
            "delta_chain_cost_eth": b1_cost - b0_cost,
            "b0_user_chain_eth": b0_cost,
            "b0_service_chain_eth": Decimal(0),
            "b1_user_chain_eth": alpha * b1_cost,
            "b1_service_chain_eth": (1 - alpha) * b1_cost,
            "extra_service_fee_eth": Decimal(0),
            "b0_unknown_charge_terms": issuer_terms("b0", issue_count, refreshes),
            "b1_unknown_charge_terms": issuer_terms("b1", issue_count, refreshes),
            "b1_user_unknown_charge_terms": issuer_terms("b1", issue_count, refreshes, alpha),
            "b1_service_unknown_charge_terms": issuer_terms("b1", issue_count, refreshes, 1 - alpha),
            "issuer_cost_status": "unknown_prices" if issue_count + refreshes else "known_zero_no_issuer_events",
            "total_cost_status": "incomplete_issuer_or_other_costs_not_total_service_cost",
            "measurement_environment": "local_evm_not_mainnet",
            "derivation_status": "event_model_projection_not_270_executed_traces",
            "fixed_deployment_cost_included": False,
        })
    return rows


def price_inputs() -> list[dict[str, str]]:
    rows = []
    for variant in ("b0", "b1"):
        for event in ("initial_issuance", "credential_refresh"):
            rows.append({
                "price_id": f"{variant}_{event}",
                "applies_to": f"{variant} {event}",
                "value": "",
                "currency": "UNSPECIFIED",
                "per_unit": "event",
                "evidence_status": "unknown",
                "source_ref": "",
                "note": "No numerical full-cost total is computed; refresh is not assumed to repeat full KYC.",
            })
    rows.append({
        "price_id": "ETH_EUR", "applies_to": "optional_currency_conversion", "value": "",
        "currency": "EUR", "per_unit": "ETH", "evidence_status": "unknown",
        "source_ref": "", "note": "ETH costs are reported without an invented current exchange rate.",
    })
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to export an empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: number(value) if isinstance(value, (Decimal, Fraction)) else "" if value is None else value
                for key, value in row.items()
            })


def export(measurements: Path, out: Path) -> dict[str, Any]:
    raw = measurements.read_bytes()
    payload = json.loads(raw)
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    source_sha = next((metadata[key] for key in ("source_sha", "source_commit", "git_commit", "commit") if metadata.get(key)), "unknown")
    provenance = {
        "source_sha": source_sha,
        "source_tree_sha256": metadata.get("source_tree_sha256", "unknown"),
        "source_dirty": metadata.get("source_dirty", "unknown"),
        "measurements_sha256": hashlib.sha256(raw).hexdigest(),
        "economics_exporter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "measurement_source": str(measurements),
    }
    summaries = summarise_events(payload)
    scenarios = build_scenarios(summaries)
    # Calculate and validate all rows before creating output files.
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "event_measurements.csv", [dict(row, **provenance) for row in summaries])
    write_csv(out / "price_inputs.csv", price_inputs())
    write_csv(out / "scenario_results.csv", [dict(row, **provenance) for row in scenarios])
    return {"scenario_count": len(scenarios), "event_metric_count": len(summaries), "source_sha": source_sha, "output_directory": str(out)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = export(args.measurements, args.out)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"economics export failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
