# Revocation timing: bounded sensitivity and provenance, v0.11

This follow-up addresses the next review without changing the original or v0.10
EVM evidence. The component, gas accounting and measured controls remain those
documented in [v0.10](REVOCATION_REVIEW_V010.md).

## What the sensitivity establishes

Twelve explicitly specified model configurations evaluate 39,843 date pairs.
There are no new EVM runs in this follow-up. The main reference remains two
distinct uniform integer days from 1–89, 100 accesses at 0,0.9,…,89.1, a 30-day
rolling TTL and credential expiry on day 90.

| Change from reference | Mean full ZK authorizations | Selective signed count | ZK higher gas, fixed means |
| --- | ---: | ---: | ---: |
| None | 4.5692 | 3 | 57.07% |
| TTL 7 days | 13.8274 | 13 | 100% |
| TTL 14 days | 7.7275 | 7 | 100% |
| TTL 60 days | 3.3021 | 2 | 0% |
| 10 accesses, 9-day spacing | 3.7033 | 3 | 100% |
| 50 accesses, 1.8-day spacing | 4.5128 | 3 | 100% |
| 200 accesses, 0.45-day spacing | 4.6218 | 3 | 0% |
| Credential expiry day 120 | 4.5692 | 3 | 57.07% |
| Two days at most 1 day apart | 4.9091 | 3 | 90.91% |
| Two days at most 7 days apart | 4.8353 | 3 | 83.53% |
| 20 bursts of 5 accesses | 4.3373 | 3 | 35.88% |

The short-credential configuration (expiry day 60) accepts 67 accesses and marks
the remaining 33 ineligible. It does not invent credential renewal, rejected-
transaction receipts or a comparable gas total for the complete 100-access trace.
Raising expiry from day 90 to day 120 leaves the count distribution unchanged
but raises mean later deadline changes from 3.1517 to 3.5692; the historical
fixed means do not capture that storage-write difference.

At a fixed 90-day horizon, regular count and frequency are coupled by h=90/n.
The burst variant holds count and first/last access fixed, with four 0.1-day
gaps inside each burst and equally spaced burst starts (integer-second rounding).
The clustered update laws are uniform conditional subsets with day gap <=1
(88 pairs) or <=7 (595 pairs). They are controlled alternatives to the full
uniform grid, not empirical correlated-arrival estimates or Poisson models.

All gas shares compare cached paths using the historical fixed unit means;
they do not reselect direct/cache implementations or assert state-calibrated
gas outside the four executed schedules. Counts are checked independently for
every pair by an event-queue implementation. Nine tests cover the original
DP/renewal model, expiry boundaries, clustered-law support, all sensitivity
pairs and deliberate mutation of the source gas CSV.

The Poisson expected-gas crossing near 2.03 relevant updates per 90 days is a
conditional fixed-mean projection, not service break-even. For exactly three
uniform distinct update days, 94.17% of schedules exceed the signed gas projection.
Increasing the number of holders raises the shared update rate only under an
additional per-holder-rate assumption (for independent rates r_i, lambda=sum r_i).
Neither the number of holders nor issuer-group cardinality alone specifies an
arrival law or anonymity entropy.

## Provenance and CI

`revocation_model.py` reconstructs its four gas constants from the exact cells
in `projects/pets4defi/data/event_costs.csv` using Decimal arithmetic and fails
on disagreement, including under Python optimization. Both model summaries
record that source SHA-256. Historical economic archives are unchanged.

The v0.10 setup script is preserved byte-for-byte under
`scripts/historical_sources/v0.10/setup.mjs`. The checker permits only that
exact executed setup snapshot, alongside the existing v0.9 runner/package
snapshots. Contract, circuit, fixture and lockfile hashes remain strict.

The prior PR CI verified the saved evidence and proofs but both demo jobs
timed out while re-verifying the complete pinned public powers-of-tau ceremony.
Default setup now verifies its published BLAKE2b-512 digest; an explicit
`--verify-public-phase1` option retains full ceremony verification. The
`--local-demo` path still performs algebraic transcript verification. Every
new circuit-specific zkey is verified as before. This is not a production setup.

CI checks nine numeric tests, exact reproduction of both saved model result
directories, all old/new receipts and 38+90 saved proofs, before fresh demo
and policy checks on both Node configurations.

## Evidence to manuscript mapping

Paths below are relative to `examples/pets4defi_access_v2/`.

| Manuscript item | Data | Reproducer/checker |
| --- | --- | --- |
| Two-day distribution; Figure 1 | `results/revocation_model/two_revocations.csv` | `scripts/revocation_model.py` |
| Original contract timing; Figure 2 | `results/revocation_validation/traces.json`, `analysis_summary.json` | `scripts/check_revocation_validation.py` |
| Fixed-m and Poisson results; Figure 3 | `results/revocation_model/fixed_m.csv`, `poisson.csv`, `summary.json` | `scripts/revocation_model.py`, `scripts/test_revocation_model.py` |
| Replay and signed-control table | `results/revocation_review/validation_report.json`, `traces.json`, `receipts_and_proofs.json.gz` | checker with `--out results/revocation_review` |
| Issuer-partition table | same report, `partitions` | same checker and saved-proof verifier |
| Historical server proving; Figure 4 | `results/server_prover.json` | original timing records; not fresh device measurements |
| Conditional schedule finance; Figure 5 | `results/revocation_model/schedule_economics.csv` | `scripts/revocation_model.py` |
| Sensitivity appendix table | `results/revocation_sensitivity/scenarios.csv`, `pairs.csv.gz`, `summary.json` | `scripts/revocation_sensitivity.py`, `scripts/test_revocation_sensitivity.py` |
| Historical unit gas | `../../projects/pets4defi/data/event_costs.csv` | `validated_unit_costs()` source guard |

The manuscript package has a separate checksum-verified plotting/table script.
Raw traces retain their original null Git metadata and exact executed source
hashes. A later integration commit does not retroactively become the run's HEAD.

## Reproduce without writing over evidence

From `examples/pets4defi_access_v2`:

```sh
python3 scripts/check_revocation_validation.py
python3 scripts/check_revocation_validation.py --out results/revocation_review
python3 -m unittest discover -s scripts -p 'test_revocation*.py' -v
python3 scripts/revocation_model.py --out /tmp/pets4defi-model-v011
diff -r results/revocation_model /tmp/pets4defi-model-v011
python3 scripts/revocation_sensitivity.py --out /tmp/pets4defi-sensitivity-v011
diff -r results/revocation_sensitivity /tmp/pets4defi-sensitivity-v011
npm ci
node scripts/verify_revocation_proofs.mjs
node scripts/verify_revocation_proofs.mjs --out results/revocation_review
```
