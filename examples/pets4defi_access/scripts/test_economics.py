"""Accounting/expiry regression checks using a small, transparent receipt fixture."""

import copy
import csv
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import economics


def fixture():
    events = []
    entries = (
        ("shared", "approve", (40, 60), None),
        ("baseline", "deposit_first", (110, 130), None),
        ("baseline", "deposit_repeat", (70, 90), None),
        ("zk", "deposit_first", (280, 320), (30, 50)),
        ("zk", "deposit_repeat", (180, 220), (10, 30)),
        ("shared", "deploy_token", (1000000,), None),
    )
    for variant, event, gas_values, proof_times in entries:
        for run, gas in enumerate(gas_values):
            events.append({
                "variant": variant, "event": event, "run": run, "gas_used": gas,
                "proof_time_ms": proof_times[run] if proof_times else None,
                "offchain_verify_ms": 5 if proof_times else None,
                "tx_hash": f"fixture-{variant}-{event}-{run}",
                "evidence_status": "measured_local",
                "scope": "shared_fixed" if event.startswith("deploy") else "per_action",
            })
    return {"schema_version": 1, "metadata": {"source_sha": "fixture-commit", "source_tree_sha256": "fixture-tree", "source_dirty": True}, "events": events}


class ExpiryTests(unittest.TestCase):
    def test_last_access_not_horizon_end_triggers_refresh(self):
        for cohort in ("new", "returning"):
            for lifetime in (30, 90, 365):
                self.assertEqual(economics.renewal_count(1, lifetime, cohort=cohort), 0)

    def test_exact_expiry_is_not_still_valid(self):
        # Accesses at days 0, 30, 60; each refresh starts its own 30-day interval.
        self.assertEqual(economics.renewal_count(3, 30, cohort="new"), 2)
        # Returning 90-day credential has 45 days left; second access is at 45.
        self.assertEqual(economics.renewal_count(2, 90, cohort="returning"), 1)

    def test_refresh_on_use_not_automatic_calendar_renewal(self):
        self.assertEqual(economics.renewal_count(10, 30, cohort="new"), 2)
        # Returning user's refreshes: days 18 and 54. No request after expiry 84.
        self.assertEqual(economics.renewal_count(10, 30, cohort="returning"), 2)
        # More frequent use triggers refreshes at 15.3, 45.9, 76.5 instead.
        self.assertEqual(economics.renewal_count(100, 30, cohort="returning"), 3)
        self.assertEqual(economics.renewal_count(100, 365, cohort="returning"), 0)


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.summaries = economics.summarise_events(fixture())
        self.rows = economics.build_scenarios(self.summaries)

    def row(self, cohort="new", n=10, alpha="0.25", gas=10, lifetime=30):
        return next(row for row in self.rows if (
            row["cohort"], row["n_accesses"], row["alpha_user"], row["gas_price_gwei"], row["validity_days"]
        ) == (cohort, n, Decimal(alpha), gas, lifetime))

    def test_complete_unique_grid(self):
        self.assertEqual(len(self.rows), 270)
        self.assertEqual(len({row["scenario_id"] for row in self.rows}), 270)

    def test_cash_allocation_does_not_create_resource_savings(self):
        for row in self.rows:
            self.assertEqual(row["b1_user_chain_eth"] + row["b1_service_chain_eth"], row["b1_chain_cost_eth"])
            self.assertEqual(row["b0_user_chain_eth"], row["b0_chain_cost_eth"])
        base = self.row()
        for alpha in ("0", "0.25", "0.5", "0.75", "1"):
            current = self.row(alpha=alpha)
            self.assertEqual(current["b1_gas_total"], base["b1_gas_total"])
            self.assertEqual(current["b1_prover_ms_total"], base["b1_prover_ms_total"])
            self.assertEqual(current["b1_refresh_count"], base["b1_refresh_count"])

    def test_first_repeat_state_and_sunk_onboarding_are_distinct(self):
        new = self.row()
        returning = self.row(cohort="returning")
        self.assertEqual(new["b0_gas_total"], 890)  # 50 + 120 + 9*80
        self.assertEqual(new["b1_gas_total"], 2150)  # 50 + 300 + 9*200
        self.assertEqual(new["b1_prover_ms_total"], 300)  # 10 * pooled (30+50+10+30)/4
        self.assertEqual(returning["b1_prover_ms_total"], new["b1_prover_ms_total"])
        self.assertEqual(returning["b0_gas_total"], 800)
        self.assertEqual(returning["b1_gas_total"], 2000)
        self.assertEqual(returning["approve_count"], 0)
        self.assertEqual(returning["b1_issue_count"], 0)
        # The enormous fixture deployment is deliberately excluded from both.
        self.assertFalse(new["fixed_deployment_cost_included"])
        self.assertEqual(new["revocation_event_count"], 0)
        self.assertEqual(new["derivation_status"], "event_model_projection_not_270_executed_traces")

    def test_gwei_conversion_and_price_change(self):
        low, high = self.row(gas=1), self.row(gas=100)
        self.assertEqual(low["b1_chain_cost_eth"], Decimal("0.000002150"))
        self.assertEqual(high["b1_chain_cost_eth"], low["b1_chain_cost_eth"] * 100)
        self.assertEqual(high["b1_gas_total"], low["b1_gas_total"])
        self.assertEqual(high["b1_refresh_count"], low["b1_refresh_count"])

    def test_unknown_prices_do_not_become_zero_totals(self):
        row = self.row()
        self.assertEqual(row["b1_unknown_charge_terms"], "1 * b1_initial_issuance + 2 * b1_credential_refresh")
        self.assertEqual(row["b1_user_unknown_charge_terms"], "0.25 * b1_initial_issuance + 0.5 * b1_credential_refresh")
        self.assertEqual(row["issuer_cost_status"], "unknown_prices")
        zero_event = self.row(cohort="returning", n=1, lifetime=365)
        self.assertEqual(zero_event["b1_unknown_charge_terms"], "0")
        self.assertEqual(zero_event["issuer_cost_status"], "known_zero_no_issuer_events")
        self.assertIn("not_total_service_cost", zero_event["total_cost_status"])
        self.assertTrue(all(row["value"] == "" for row in economics.price_inputs()))

    def test_missing_gas_fails_instead_of_producing_false_cheap_result(self):
        data = fixture()
        data["events"] = [event for event in data["events"] if not (event["variant"] == "zk" and event["event"] == "deposit_repeat")]
        with self.assertRaisesRegex(ValueError, "missing measured metric"):
            economics.build_scenarios(economics.summarise_events(data))

    def test_missing_prover_measurement_is_visible(self):
        data = fixture()
        for event in data["events"]:
            event["proof_time_ms"] = None
        row = economics.build_scenarios(economics.summarise_events(data))[0]
        self.assertIsNone(row["b1_prover_ms_total"])
        self.assertEqual(row["prover_time_status"], "missing_measurement")

    def test_timing_pool_weights_samples_not_event_group_means(self):
        data = fixture()
        data["events"] = [event for event in data["events"] if not (event["variant"] == "zk" and event["event"] == "deposit_first" and event["run"] == 1)]
        rows = economics.build_scenarios(economics.summarise_events(data))
        # One first proof (30 ms), two repeats (10 and 30 ms): 70/3, not 25.
        self.assertEqual(rows[0]["b1_prover_ms_per_access"], Decimal(70) / 3)
        self.assertEqual(rows[0]["b1_prover_samples"], 3)

    def test_partial_proof_timing_does_not_become_a_complete_estimate(self):
        data = fixture()
        next(event for event in data["events"] if event["variant"] == "zk" and event["event"] == "deposit_repeat")["proof_time_ms"] = None
        row = economics.build_scenarios(economics.summarise_events(data))[0]
        self.assertIsNone(row["b1_prover_ms_total"])
        self.assertEqual(row["prover_time_status"], "missing_measurement")

    def test_nonfinite_or_unmeasured_inputs_are_rejected(self):
        for field, value in (("gas_used", -1), ("proof_time_ms", float("nan")), ("gas_used", 2.5), ("evidence_status", "assumed")):
            data = copy.deepcopy(fixture())
            data["events"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                economics.summarise_events(data)

    def test_export_preserves_provenance_and_blank_price_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "measurements.json"
            source.write_text(json.dumps(fixture()), encoding="utf-8")
            out = Path(tmp) / "out"
            result = economics.export(source, out)
            self.assertEqual(result["scenario_count"], 270)
            with (out / "scenario_results.csv").open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 270)
            self.assertEqual(rows[0]["source_sha"], "fixture-commit")
            self.assertEqual(rows[0]["source_tree_sha256"], "fixture-tree")
            self.assertEqual(rows[0]["source_dirty"], "True")
            self.assertEqual(len(rows[0]["measurements_sha256"]), 64)
            self.assertEqual(len(rows[0]["economics_exporter_sha256"]), 64)
            with (out / "price_inputs.csv").open(newline="", encoding="utf-8") as stream:
                self.assertTrue(all(row["value"] == "" for row in csv.DictReader(stream)))


if __name__ == "__main__":
    unittest.main()
