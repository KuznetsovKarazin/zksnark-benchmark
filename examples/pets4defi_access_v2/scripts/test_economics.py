"""Behavioral accounting tests against small, inspectable event fixtures."""

import copy
import csv
import json
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import economics as e


def fixture(chains=("l1",)):
    events = []
    for chain in chains:
        multiplier = 1 if chain == "l1" else 2

        def add(variant, event, gas, *, count=1, scope="per_action", proof=None):
            for run in range(count):
                current = gas[run % len(gas)] if isinstance(gas, list) else gas
                events.append({"chain": chain, "variant": variant, "event": event, "run": run,
                               "gas_used": current * multiplier, "proof_time_ms": None if proof is None else proof + run % 3,
                               "tx_hash": f"fixture-{chain}-{variant}-{event}-{run}", "scope": scope, "evidence_status": "measured_local"})

        for event, value in (("deploy_poseidon", 30), ("deploy_registry", 50), ("deploy_token", 20), ("deploy_verifier", 100)):
            add("shared", event, value, scope="shared_fixed")
        add("shared", "issuer_root_initial", 5, count=4, scope="shared_fixed")
        add("shared", "issuer_root_update", [24, 25, 26], count=30, scope="per_registry_update")
        for variant in e.VARIANTS:
            zk, cached = variant.startswith("zk"), variant.endswith("cache")
            add(variant, "approve", 10)
            add(variant, "deploy_gate", (330 if cached else 300) if zk else (220 if cached else 200), scope="shared_fixed")
            add(variant, "bootstrap_token_balance", 10, scope="shared_fixed")
            if cached:
                add(variant, "cache_register_first", 500 if zk else 150, proof=950 if zk else None)
                add(variant, "cache_hit", 20, count=30)
                add(variant, "cache_reauthorize", 350 if zk else 80, count=30, proof=200 if zk else None)
            else:
                add(variant, "access_first", 400 if zk else 100, proof=900 if zk else None)
                add(variant, "access_repeat", 300 if zk else 50, count=30, proof=100 if zk else None)
    return {"schema_version": 2, "metadata": {"source_sha": "fixture-commit", "source_tree_sha256": "fixture-tree", "source_dirty": False}, "events": events}


class TraceTests(unittest.TestCase):
    def test_primary_grid_is_96_workloads_not_a_price_or_alpha_grid(self):
        contexts = e.contexts()
        self.assertEqual(len(contexts), 96)
        self.assertEqual(len({x.context_id for x in contexts}), 96)

    def test_total_demand_and_one_credential_are_preserved_across_apps(self):
        stats, rows = e.trace(e.Context(10, 5, 10, 90, "none"))
        self.assertEqual(len(rows), 10)
        self.assertEqual(stats["credential_issues_per_user"], 1)
        self.assertEqual(stats["approve"], 5)
        self.assertEqual(stats["access_first"], 5)
        self.assertEqual(stats["access_repeat"], 5)
        tiny, _ = e.trace(e.Context(1, 5, 10, 30, "daily"))
        self.assertEqual(tiny["apps_visited_per_user"], 1)
        self.assertEqual(tiny["approve"], 1)
        self.assertEqual(tiny["credential_refreshes_per_user"], 0)

    def test_authorization_ttl_is_separate_from_credential_expiry(self):
        stats, rows = e.trace(e.Context(10, 1, 10, 90, "none"))
        self.assertEqual(stats["credential_refreshes_per_user"], 0)
        self.assertEqual(stats["cache_register_first"], 1)
        self.assertEqual(stats["cache_hit"], 7)
        self.assertEqual(stats["cache_reauthorize"], 2)
        self.assertEqual([row["timestamp_days"] for row in rows if row["cache_event"] == "cache_reauthorize"], [Fraction(36), Fraction(72)])

    def test_expiry_boundary_is_not_a_valid_cache_hit(self):
        stats, rows = e.trace(e.Context(3, 1, 10, 90, "none"))
        self.assertEqual([row["cache_event"] for row in rows], ["cache_register_first", "cache_reauthorize", "cache_reauthorize"])
        self.assertEqual(stats["reauth_expiry"], 2)

    def test_registry_refreshes_are_shared_and_unbatched(self):
        stats, rows = e.trace(e.Context(10, 5, 10, 30, "none"))
        self.assertEqual(stats["credential_refreshes_per_user"], 2)
        self.assertEqual(stats["root_publications_refresh_population"], 20)
        # Renewals occur at 36 and 72, not at unused calendar times 30 and 60.
        self.assertEqual([row["timestamp_days"] for row in rows if row["credential_refresh_at_this_time"]], [Fraction(36), Fraction(72)])
        self.assertEqual(rows[4]["registry_epoch_delta"], 10)
        self.assertEqual(rows[8]["registry_epoch_delta"], 20)

    def test_population_driven_churn_can_erase_cache_reuse(self):
        small, _ = e.trace(e.Context(100, 1, 10, 90, "population_unbatched"))
        large, _ = e.trace(e.Context(100, 1, 1000, 90, "population_unbatched"))
        self.assertEqual(small["root_publications_background"], 10)
        self.assertEqual(large["root_publications_background"], 1000)
        self.assertEqual(small["cache_reauthorize"], 10)
        self.assertEqual(small["cache_hit"], 89)
        self.assertEqual(large["cache_reauthorize"], 99)
        self.assertEqual(large["cache_hit"], 0)

    def test_all_cache_hits_are_current_and_all_accesses_are_counted(self):
        for context in e.contexts():
            stats, rows = e.trace(context)
            with self.subTest(context=context.context_id):
                self.assertEqual(stats["access_first"] + stats["access_repeat"], context.n_accesses)
                self.assertEqual(stats["cache_register_first"] + stats["cache_hit"] + stats["cache_reauthorize"], context.n_accesses)
                for row in rows:
                    if row["cache_event"] == "cache_hit":
                        self.assertEqual(row["prior_cache_epoch_delta"], row["registry_epoch_delta"])
                        self.assertLess(row["timestamp_days"], row["prior_cache_until_days"])


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.measures = e.Measurements(e.summarise_events(fixture()))

    def evaluate(self, context, variant):
        stats, _ = e.trace(context)
        return e.evaluate(self.measures, context, stats, "l1", variant)

    def test_fixed_cost_is_once_then_amortized_not_repeated_per_person(self):
        small = self.evaluate(e.Context(1, 1, 10, 90, "none"), "signed_direct")
        large = self.evaluate(e.Context(1, 1, 1000, 90, "none"), "signed_direct")
        self.assertEqual(small["common_demo_setup_gas_once"], 120)  # Includes four initial roots, not their mean.
        self.assertEqual(small["all_demo_setup_gas_once"], 330)
        self.assertEqual(large["all_demo_setup_gas_once"], 330)
        self.assertEqual(small["demo_setup_gas_per_user"], 33)
        self.assertEqual(large["demo_setup_gas_per_user"], Decimal("0.33"))
        self.assertEqual(small["user_action_gas_per_user"], 110)
        self.assertEqual(large["user_action_gas_per_user"], 110)

    def test_population_renewal_fee_is_not_charged_N_times_to_each_user(self):
        row = self.evaluate(e.Context(10, 1, 10, 30, "none"), "signed_cache")
        self.assertEqual(row["root_publications_total"], 20)
        self.assertEqual(row["registry_update_gas_population"], 500)
        self.assertEqual(row["registry_update_gas_per_user"], 50)
        self.assertEqual(row["unknown_issuer_charge_expression"], "1 * p_signed_initial_issuance + 2 * p_signed_credential_refresh")

    def test_verifier_fixed_cost_is_only_assigned_to_zk(self):
        context = e.Context(1, 1, 10, 90, "none")
        self.assertEqual(self.evaluate(context, "signed_direct")["verifier_setup_gas_once"], 0)
        self.assertEqual(self.evaluate(context, "zk_direct")["verifier_setup_gas_once"], 100)

    def test_caching_reduces_proof_count_not_per_proof_runtime(self):
        context = e.Context(10, 1, 10, 90, "none")
        direct, cache = (self.evaluate(context, variant) for variant in ("zk_direct", "zk_cache"))
        self.assertEqual(direct["proofs_per_user"], 10)
        self.assertEqual(cache["proofs_per_user"], 3)
        self.assertEqual(direct["warm_proof_ms_per_proof"], 151)
        self.assertEqual(cache["warm_proof_ms_per_proof"], 151)
        self.assertEqual(direct["derived_prover_ms_per_user"], 1510)
        self.assertEqual(cache["derived_prover_ms_per_user"], 453)

    def test_break_even_equation_accounts_for_bundled_deposit(self):
        context = e.Context(10, 1, 10, 90, "none", auth_ttl_days=90)
        stats, _ = e.trace(context)
        direct, cache = (self.evaluate(context, variant) for variant in ("signed_direct", "signed_cache"))
        result = e.break_even(self.measures, context, stats, "l1", "signed", direct, cache)
        self.assertEqual(result["headroom_before_reauthorizations_gas_per_user"], 218)
        self.assertEqual(result["additional_gas_per_reauthorization"], 60)
        self.assertEqual(result["max_reauthorizations_for_strict_saving"], 3)
        self.assertEqual(result["cached_gas_saving_per_user"], 218)
        self.assertTrue(result["cache_saves_gas_this_trace"])

    def test_cache_can_lose_under_churn_instead_of_assuming_it_always_wins(self):
        context = e.Context(10, 1, 10, 90, "daily")
        stats, _ = e.trace(context)
        direct, cache = (self.evaluate(context, variant) for variant in ("signed_direct", "signed_cache"))
        result = e.break_even(self.measures, context, stats, "l1", "signed", direct, cache)
        self.assertEqual(result["actual_reauthorizations"], 9)
        self.assertEqual(result["cached_gas_saving_per_user"], -322)
        self.assertFalse(result["cache_saves_gas_this_trace"])

    def test_statistics_include_median_iqr_and_actual_sample_count(self):
        row = self.measures.index[("l1", "shared", "issuer_root_update", "gas_used")]
        self.assertEqual(row["n"], 30)
        self.assertEqual(row["mean"], 25)
        self.assertEqual(row["median"], 25)
        self.assertEqual(row["iqr"], 2)
        first = self.measures.index[("l1", "zk_direct", "access_first", "gas_used")]
        self.assertEqual(first["n"], 1)
        self.assertEqual(first["sample_interpretation"], "single_observation")

    def test_missing_measured_cost_fails_instead_of_becoming_zero(self):
        payload = fixture()
        payload["events"] = [row for row in payload["events"] if row["event"] != "issuer_root_update"]
        measures = e.Measurements(e.summarise_events(payload))
        context = e.Context(10, 1, 10, 90, "daily")
        stats, _ = e.trace(context)
        with self.assertRaisesRegex(ValueError, "missing/incomplete measured gas"):
            e.evaluate(measures, context, stats, "l1", "zk_cache")

    def test_partial_timing_is_not_silently_a_complete_result(self):
        payload = fixture()
        row = next(row for row in payload["events"] if row["variant"] == "zk_cache" and row["event"] == "cache_reauthorize")
        row["proof_time_ms"] = None
        measures = e.Measurements(e.summarise_events(payload))
        context = e.Context(10, 1, 10, 90, "none")
        stats, _ = e.trace(context)
        result = e.evaluate(measures, context, stats, "l1", "zk_cache")
        self.assertIsNone(result["derived_prover_ms_per_user"])
        self.assertEqual(result["prover_time_status"], "missing_warm_measurement")

    def test_op_execution_component_is_never_labelled_full_fee(self):
        measures = e.Measurements(e.summarise_events(fixture(("l1", "op"))))
        context = e.Context(1, 1, 10, 90, "none")
        stats, _ = e.trace(context)
        row = e.evaluate(measures, context, stats, "op", "signed_direct")
        self.assertEqual(row["fee_boundary"], "execution_only_excludes_L1_data_and_operator_fees")
        prices = e.price_sensitivity([row])
        self.assertEqual(len(prices), 4)
        self.assertTrue(all("excludes_L1_data" in price["fee_boundary"] for price in prices))
        self.assertEqual(prices[-1]["known_execution_eth_per_user"], row["known_execution_gas_per_user"] * Decimal("1e-8"))
        self.assertTrue(all(price["value"] == "" for price in e.price_inputs()))

    def test_reject_invalid_measured_inputs(self):
        for field, value in (("gas_used", -1), ("gas_used", 2.5), ("proof_time_ms", float("nan")), ("evidence_status", "assumed")):
            payload = copy.deepcopy(fixture())
            payload["events"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                e.summarise_events(payload)

    def test_observed_price_uses_correct_network_wei_and_preserves_window(self):
        measures = e.Measurements(e.summarise_events(fixture(("l1", "op"))))
        context = e.Context(1, 1, 10, 90, "none")
        stats, _ = e.trace(context)
        results = [e.evaluate(measures, context, stats, chain, "signed_direct") for chain in ("l1", "op")]
        snapshot = {"status": "available", "raw_archive": {"path": "fixture.json.gz", "sha256": "a" * 64}, "networks": []}
        for network, price in (("ethereum", 100_000_000), ("optimism", 8000)):
            snapshot["networks"].append({
                "network": network, "status": "available", "source_url": "fixture://rpc",
                "window": {"first_block": {"number": 100, "timestamp_utc": "2026-10-19T00:00:00+00:00"},
                           "last_block": {"number": 199, "timestamp_utc": "2026-10-20T00:00:00+00:00"},
                           "boundary_timestamp_span_seconds": 86400, "block_count": 100},
                "summary": {"within_block_effective_p50_block_weighted": {
                    "p10_wei": str(price // 2), "p50_wei": str(price), "p90_wei": str(2 * price), "observations": 100}},
            })
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fee_snapshot.json"
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            rows = e.observed_fee_projection(results, path)
            self.assertEqual(len(rows), 6)
            l1, op = [row for row in rows if row["block_distribution_percentile"] == 50]
            self.assertEqual(l1["observed_execution_price_proxy_gwei"], Decimal("0.1"))
            self.assertEqual(op["observed_execution_price_proxy_gwei"], Decimal("0.000008"))
            self.assertEqual(op["known_execution_eth_per_user"], results[1]["known_execution_gas_per_user"] * Decimal("8e-15"))
            self.assertIn("not_global_transaction_quantile", op["price_metric"])
            self.assertIn("excludes_L1_data_and_operator", op["fee_boundary"])
            self.assertEqual(l1["window_start_utc"], "2026-10-19T00:00:00+00:00")
            self.assertEqual(l1["raw_fee_archive_sha256"], "a" * 64)
            del snapshot["networks"][1]
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "do not substitute another chain"):
                e.observed_fee_projection(results, path)

    def test_allocation_is_a_conserved_transfer_not_a_new_workload_grid(self):
        rules = e.allocation_rules()
        self.assertEqual([row["user_share_alpha"] for row in rules], list(map(Decimal, ("0", ".25", ".5", ".75", "1"))))
        fee = Decimal("0.000012345")
        for row in rules:
            self.assertEqual(fee * row["user_share_alpha"] + fee * row["sponsor_share"], fee)
            self.assertIn("unknown_issuer", row["cost_pool"])
            self.assertIn("actual_transaction_sender_is_unchanged", row["interpretation"])

    def test_export_counts_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "measurements.json"
            source.write_text(json.dumps(fixture(("l1", "op"))), encoding="utf-8")
            out = Path(directory) / "results"
            result = e.export(source, out)
            self.assertEqual(result["workload_contexts"], 96)
            self.assertEqual(result["architecture_chain_results"], 768)
            self.assertEqual(result["price_rows_are_postprocessing"], 3072)
            self.assertEqual(result["observed_fee_projection_rows"], 0)
            self.assertEqual(result["observed_fee_status"], "not_supplied_no_prices_imputed")
            self.assertEqual(result["allocation_rules"], 5)
            with (out / "architecture_results.csv").open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 768)
            self.assertEqual(rows[0]["source_sha"], "fixture-commit")
            self.assertEqual(rows[0]["source_dirty"], "False")
            self.assertEqual(len(rows[0]["measurements_sha256"]), 64)
            self.assertEqual(len(rows[0]["economics_exporter_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
