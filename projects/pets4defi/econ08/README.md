# ECON-07 + ECON-08 evidence and research plan v0.4

The active direction is [protocol v0.4](handoff/ECON07_08_Research_Protocol_v0_4.docx) and the [implementation plan](IMPLEMENTATION_PLAN_V04.md), dated 13 November 2026. The accepted ECON-07 package and archived measurements remain unchanged. The timed diagnostic reuses eight existing cohort traces; it adds no new EVM measurements.

The candidate contribution is revocation induced liquidity spillover: how shared status changes affect the funds required before the next refill, as eligible holders return and renew authorizations. Two fixed rules compare SELF payments with a prepaid PM account covering holder operations; operator/issuer shared costs remain separate. Daily refill is primary, with weekly and no-refill controls. PUB-01 already covers counts, timing, grouping, TTL and gas; ECON-07 covers lifecycle payments and funds. A new article needs an additional result from event timing and fixed financing rules. The initial replay leaves G0a open: startup dominates the full-lifecycle daily/weekly target, which is almost identical across B1/B2/B4. The next bounded study predeclares startup versus continuing-service reporting and matched access/TTL phases.

## Start here

- **Nataliya:** [START_HERE](handoff/START_HERE.md), [protocol](handoff/ECON07_08_Research_Protocol_v0_4.docx), and [download the current handoff ZIP](handoff/ECON08_Nataliya_First_Checkpoint.zip). The packet is self-contained for reading, includes three ten-column templates and original summary CSVs, and needs no installation or GitHub access. Optional technical material is labelled for information only. First return: a 2–3 page note, one worked example and the starter tables. Soft target: 30 November 2026, adjustable together.
- **Oleksandr:** [plan v0.4](IMPLEMENTATION_PLAN_V04.md). G0a tests the scientific case before new modeling or EVM work. Use the fixed [financing rules](handoff/FINANCING_RULES.md) and [timed diagnostic](handoff/optional/liquidity/LIQUIDITY_NOTE.md). Direct gas is a PM proxy without measured account-abstraction overhead. The v0.3 operator-only sponsor construction is archived history, not the PM rule or evidence that G0a passed.
- **Technical evidence:** [validation](VALIDATION.md), [pilot](RESULTS.md), [cohort](COHORT.md). The handoff includes optional reading copies with local links.
- **Source and recovery:** [research branch](https://github.com/KuznetsovKarazin/zksnark-benchmark/tree/econ08-native-pilot) and [original source bundle](ECON08_source.bundle). The full reproduction commands below require the source repository or recovery package, not the economics packet alone. Current checks are internal validation; independent reproduction remains open.

The preserved evidence consists of 32 pilot and 22 cohort scenarios, 8832 ordinary accesses and 512 proofs including 33 timing proofs. Cohort N=16/128/512 counts issued credentials but only four active wallets. W3C is a qualitative comparator; PRC and CRSet remain related work. Historical component timings are not an alternative full-service gas price.

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

## Nataliya's next small deliverable

Use [START_HERE](handoff/START_HERE.md): map accepted K01–K16 to events and actors, source prices or mark unknowns, and calculate required holder, prepaid-account and shared-actor funding under the fixed SELF/PM rules. Budgets are outputs, not assumed willingness to pay. Measured quantities remain in the original summaries; templates contain 10 columns each. Return a short note, one worked case and missing inputs. The technical plan is for information only. Soft target: 30 November 2026, adjustable together.

## What remains before a new publication

- G0a must establish a substantive timing/liquidity result beyond PUB-01 and ECON-07. A constructed cap, a familiar payment architecture or a no-refill cumulative-cost identity is insufficient by itself.
- Exact independent replay of 54 archived scenarios, then only the expectation and robustness extensions needed for the selected question.
- One A=32 EVM workload configuration with matched mechanisms and no-update controls, at N≥32 within capacity. δ=3/7/14 days remains model-only; A64 and contract changes are deferred.
- Own-revocation/reissuance economics is deferred. Existing security rejection checks remain required.
- Sourced prices, one full L2 fee model, and validated funding/liquidity frontiers. No assertion of an L1 threshold or no L2 effect before calculation.
- Fresh figures and explicit overlap review. No external PRC adapter or W3C gas comparison is required.

Delta is measured from authoritative publication; issuer reporting delay remains outside that clock. B=1/2/4 corresponds to potential issuer sets 4/2/1 conditional on metadata, not anonymity entropy. Wallet linkage remains. No user adoption, profitability, market willingness to pay or production-security claim is established by these experiments.
