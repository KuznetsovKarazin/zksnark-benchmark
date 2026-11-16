# ECON-07 + ECON-08 research status

**16 November 2026: observability pilot v0.2 is the current technical checkpoint.**
The [new pilot](observability_v02/README.md) includes scoped optimality proofs,
one-coin-per-publication experiments, anonymous-publication clustering, the full
availability sensitivity grid, and economic externality inputs. It uses archived
gas coefficients; no new EVM measurement or deployment-security claim is made.
Scientific novelty still requires independent review.

Nataliya's Economic Addendum v0.2.1 completes the earlier funding task. Its small
pooling effect and the distinction between retained capital and gas expenditure
remain accepted. The new assignment concerns **who pays the cost of hiding issuer
reactions and how issuer compensation changes that burden**. It does not reopen the
pooling calculation. Soft first-return target: **30 November 2026**, adjustable.

## Current entry points

- **Nataliya:** [short instructions](observability_v02/handoff/START_HERE.md),
  [prefilled payment table](observability_v02/handoff/payment_comparison_REFERENCE.csv),
  [historical price inputs](observability_v02/handoff/price_inputs.csv).
  Return a 2–3 page note and the completed table. Start with weekly A=4, then
  compare the two compensation rules in asymmetric A=32; the latter is modeled.
- **Complete standalone download:** [ECON08 Observability v0.2 ZIP](packages/ECON08_Observability_v0_2_2026-11-16.zip).
  Contains code, inputs, all numeric outputs, figures, proofs and the handoff.
- **Oleksandr and reviewer:** [six-page Russian PDF](observability_v02/ECON08_Observability_Review_RU_v0_2.pdf),
  [proofs](observability_v02/proofs/CONDITIONAL_RESULTS.md),
  [model](observability_v02/MODEL.md), [validation](observability_v02/results/validation.json).
- **Completed preceding work:** [funding follow-up v0.5](technical_followup_v05/README.md)
  and [original v0.4 assignment](handoff/START_HERE.md). Their historical deadlines
  are not new pending tasks. Accepted ECON-07 and original measured evidence remain unchanged.
- **Research branch:** [econ08-native-pilot](https://github.com/KuznetsovKarazin/zksnark-benchmark/tree/econ08-native-pilot).
  [PR #3](https://github.com/KuznetsovKarazin/zksnark-benchmark/pull/3) remains unmerged.
  Reproduction is internal validation, not independent external replication.

The material below documents the original EVM archive. Its measured population
and four-wallet cohort must not be confused with new modeled 16/32/64-holder grids.

## Archived v0.1 implementation

- Four native mechanisms: ZK with 1, 2 or 4 enforced issuer groups, plus a public signed-cache diagnostic control.
- Three ordinary revocation delays: 0, 3,600 and 86,400 seconds. Zero presentation grace for old roots in every run.
- A 90-day horizon, 30-day authorization lifetime and credential expiry at day 90.
- Eight synthetic credentials, two per issuer. The observed holder is issuer 0 / credential 0. The circuit's capacity of 1,024 per issuer is **not** the observed population.
- LOW: one access at day 0. HIGH: 100 accesses at `floor(i * 90 * 86400 / 100)`, `i = 0..99`.
- Other credentials revoked: issuer 3 / credential 1 at day 31, issuer 1 / credential 1 at day 63. Publications occur even in LOW after its last access. An update precedes an access at the same timestamp.
- 24 main scenario runs (12 configurations × two workloads) and 8 no-update diagnostic runs: 1,616 normal access transactions in total.
- Separate correctness traces for own revocation and deadline −1/at/+1, non-extension by a second update, immediate emergency changes, issuer partition enforcement, cross-group proofs, wrong action context, replay, stale root, expiry and ineligible witnesses. Failed transactions must leave the checked protected state unchanged.

The signed control reveals issuer/credential identity and has different privacy. It uses the common four-issuer registry/publication boundary, without a ZK verifier. Its deployment cost is not a minimal standalone signed implementation.

## Files for Nataliya

The measured package is in [`examples/pets4defi_access_v2/results/econ08_native_pilot`](../../../examples/pets4defi_access_v2/results/econ08_native_pilot).

| File | Use |
|---|---|
| `summary.csv` | One row per configuration/workload. Authorization counts and gas split by actor. |
| `cost_ledger.csv` | Every transaction, actor, category, gas and calldata size; correctness transactions are labelled separately. |
| `accesses.json` | Per-access event, reason, timestamp, state before/after, receipt and proof link. |
| `report.json` | Exact scenarios, source hashes, environment, setup, correctness cases, limitations and status. |
| `receipts_and_proofs.json.gz` | Raw transaction receipts, transaction data, synthetic witnesses, proofs and public inputs. |
| `verification_key.json`, `Verifier.sol` | Independent verification without obtaining the old proving key. |
| `manifest.json` | SHA-256 checksums for the main evidence files. |
| `timing/session_1.json` ... `session_3.json` | Fresh-process proof/verification timings and proofs, if the timing stage has been run. |
| `analysis/` | Two descriptive figures, timing quantiles and a separate manifest for derived files and timing sessions. |

**Read `report.json.status` before using a run.** `PASS` means the complete native pilot and its implemented correctness suite finished. `SMOKE_PASS` is a two-scenario diagnostic and must not be used as the full experiment. A `FAIL` or `RUNNING` directory is incomplete. The timing stage has its own completion check.

## Cost boundary

Use resource quantities before prices. The summary contains:

1. `holder_gas`: one observed holder's approval and successful accesses.
2. `operator_setup_gas`: all B registries and B gates, permanent exclusion of out-of-group issuers, one shared Poseidon and (for ZK) one shared verifier.
3. `issuer_initial_publication_gas`: all four issuers' initial roots.
4. `issuer_status_publication_gas`: both scheduled revocations, including groups the observed holder does not use.
5. `measured_boundary_gas`: sum of those four quantities. This is **shared infrastructure plus one observed holder**, not whole-population cost.
6. `excluded_fixture_gas`: mock-token deployment and one-unit gate-balance bootstrap, preserved but excluded. The initial nonzero gate balance matches the previous experiment's storage convention.

No diagnostic signed gate is charged to a ZK configuration. Correctness/failed transactions never enter the normal workload totals. Initial liquidity, reimbursements and other financial transfers are not resource costs. Issuance, witness delivery, distribution, hosting and real-world reporting latency remain **unmeasured**, not zero. Gas is not a euro price or a measured public-network fee; no new price assumptions are introduced here.

## Reproduce

From the repository root:

```sh
cd examples/pets4defi_access_v2
npm ci
npm run setup
node --test scripts/econ08/test_config.mjs
node scripts/econ08/run.mjs --out results/local/econ08_my_run
python3 scripts/econ08/check.py results/local/econ08_my_run --source-root .
node scripts/econ08/verify_proofs.mjs results/local/econ08_my_run
```

Use a **new output directory** for each run; the runner refuses to overwrite evidence. For a quick two-scenario diagnosis add `--smoke` to the runner and `--allow-smoke` to the checker. This exercises grouped ZK/LOW and signed/HIGH, not the full rejection suite.

After the full replay has finished, run these **sequentially in fresh processes**, without concurrent benchmarks:

```sh
node scripts/econ08/timing.mjs results/local/econ08_my_run 1
node scripts/econ08/timing.mjs results/local/econ08_my_run 2
node scripts/econ08/timing.mjs results/local/econ08_my_run 3
node scripts/econ08/verify_proofs.mjs results/local/econ08_my_run
```

There are ten measured `fullProve` observations per session, plus one excluded warm-up. Verification time is measured separately. This is one fixed synthetic input and one device: report sample count, p50/p95, per-session medians and warm-up separately. It does not estimate device/population variation, full network latency or throughput.

Generate the descriptive figures and timing summary after all three sessions:

```sh
python3 -m pip install matplotlib==3.10.8
python3 scripts/econ08/analyze.py results/local/econ08_my_run
```

The observed outcomes are explained in [RESULTS.md](RESULTS.md). `analysis/manifest.json` covers the timing and derived files; the main `manifest.json` remains unchanged.

The setup uses a pinned public phase-1 transcript and verifies the resulting zkey. The local phase-2 contributions are for experiments, **not a production trusted setup**. Proving randomness can change proof bytes and calldata gas slightly; compare exact counts and guarantees, and retain each run's receipts. Do not require byte-identical cryptographic outputs across fresh setups.

To audit the archived evidence without rebuilding the proving key:

```sh
git fetch projects/pets4defi/econ08/source-at-run.bundle refs/heads/econ08-native-pilot
git worktree add --detach /tmp/econ08-source-at-run FETCH_HEAD
cd examples/pets4defi_access_v2
python3 scripts/econ08/check.py results/econ08_native_pilot --source-root /tmp/econ08-source-at-run/examples/pets4defi_access_v2
node scripts/econ08/verify_proofs.mjs results/econ08_native_pilot
```

The report records the actual local source commit `012044c17d4dc98ca6eae8f696e04252f9fb0d5a`. The exact commit is preserved in [source-at-run.bundle](source-at-run.bundle), based on the public parent `53f47c383a96e86641b6a18fb98636f7ab9b5da4`. It can be inspected with `git bundle verify` and imported with `git fetch projects/pets4defi/econ08/source-at-run.bundle refs/heads/econ08-native-pilot:refs/heads/econ08-source-at-run`. The report's individual source SHA-256 values also match the delivered experiment files. The publication commit adds results, analysis and documentation without changing the executed runner.

## Nataliya's current deliverable

Use the [v0.2 task](observability_v02/handoff/START_HERE.md). The technical quantity
inputs and three reference payment rules are fixed. The note should distinguish
resource cost, transfers and net actor burden, and assess the incentive limits of
charging issuers for effects on foreign holders. Technical proofs and the full
research report are for information only for this checkpoint.

## What remains before a new article

- Independent review of the scoped lower bound and comparison with PUB-01,
  ABC4Trust and the relevant disclosure/intersection literature.
- Nataliya's bounded incidence/compensation note, including budget balance,
  administrative costs and the risk of discouraging timely revocation reporting.
- A publication decision based on distinct contribution. The pilot alone does not
  establish novelty, market adoption, willingness to pay or a viable incentive mechanism.
- No new contract, A32 EVM campaign or main-branch merge is required by this checkpoint.
  Real settlement, issuance, publication and downtime costs remain separate unknowns.

Delta is measured from authoritative publication; issuer reporting delay is
outside that clock. Fixed gas-coefficient optimality is not monetary optimality
under arbitrary time-varying prices. See the new model and counterexample.
