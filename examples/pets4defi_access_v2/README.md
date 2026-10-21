# PETs4DeFi: eligibility privacy and access architecture

For the economic assignment and a compact input dataset, use the [project page](../../projects/pets4defi/README.md).

This technical directory contains a runnable, synthetic experiment for the **cost of specified privacy properties under different access and status-update architectures**. The current policy experiment is specified below and in [POLICIES.md](POLICIES.md), with [measured results](POLICY_RESULTS.md). Earlier architecture receipts and analyses remain available in `results/`, [RESULTS.md](RESULTS.md), [THREAT_MODEL.md](THREAT_MODEL.md) and [ECONOMICS.md](ECONOMICS.md). Raw transaction receipts, proof samples and fee evidence are retained in `results/`.

## Access methods and freshness policies

| Method | Eligibility presentation | Later deposit |
|---|---|---|
| `unchecked` | None; matched transfer, nonce and accounting | Same operation |
| `signed_direct` | Registry-wide EIP-712 credential | Check signature and individual status |
| `signed_cache` | Same credential | Read authorization and individual status |
| `zk_direct` | Groth16 membership/predicate proof | Verify a fresh action-bound proof |
| `zk_cache` | Same ZK statement | Read authorization and security context |

`PolicyRegistry`, `PolicyGate` and `UncheckedDeposit` implement global publication invalidation, selective security invalidation and ordinary-revocation delays of 300 or 3,600 seconds. These are experimental settings. A separate 300-second recent-root window permits in-flight proofs after additions. Emergency issuer/policy changes invalidate immediately. An issuer's classification of an opaque root as addition-only is trusted, not cryptographically enforced.

Both signed and ZK credentials are reusable across gates. ZK hides the selected trusted issuer, credential identifier, tier, jurisdiction and Merkle paths. It exposes a different pseudonym in each application scope. Public wallets, token flows, timing and status updates remain observable. This is not end-to-end anonymity or a legal KYC implementation.

The circuit proves membership in an issuer's active credential set and a trusted-issuer registry, minimum tier, allowed-jurisdiction membership and a valid authorization window. The hierarchy has 1,024 credential slots per issuer, four issuer slots and eight policy leaves; **7,409 constraints, seven public inputs and one public output**. Only eight synthetic credentials are populated in the fixture. It uses active-set membership, not a claim of implementing a general sanctions non-membership proof.

## Reproduce

Validated runtime lines: **Node 22 with npm 10** and **Node 24 with npm 11**. Python 3.10+ is required for accounting/tests; `curl` downloads the public setup transcript. Exact npm dependencies and the lockfile are committed. Use `npm ci`, not an unpinned install.

```sh
cd examples/pets4defi_access_v2
npm ci
npm run policy
```

This runs setup, policy/transfer checks, 30-sample recurring-event measurements, economic accounting and model tests. `npm run policy:economics` rebuilds the participant tables from retained `results/policy_measurements.json`; EUR conversion uses the dated quote retained in `projects/pets4defi/data/fx_quote.json`; an explicit CLI override is labelled as an assumption. Debug runs (`BENCH_RUNS=2 npm run policy:benchmark`) are explicitly marked and rejected by the final exporter.

The current participant tables use this policy experiment. The earlier global-only architecture experiment can still be reproduced separately:

```sh
npm run demo
npm run prover
python3 scripts/report.py
python3 scripts/package_results.py
```

`demo` compiles the circuit, obtains a hash-pinned public Powers of Tau transcript, verifies the local phase-2 setup, executes both local chain environments, exports accounting tables and runs economic tests. The default is **30 warmed repetitions** of the relevant recurring events. First-holder events are explicitly single observations. `BENCH_RUNS=2 npm run benchmark` is a diagnostic run and is labelled as such in metadata; do not publish it as the main result.

Published receipt evidence comes from the complete successful Node24/npm11 CI run: see `results/ci_provenance.json` and the byte-preserved `results/raw_ci_node24.zip`. GitHub tests a temporary PR merge commit; all measured source-file hashes match the reviewed branch source. Complete CSVs are bundled in `results/economic_tables.zip`. Large derived trace/price CSVs and raw transaction receipts are retained in the archives rather than duplicated as GitHub text files.

Expected witness-generation failures in negative tests may print `ERROR`. The process exit status and `results/test_results.json` distinguish these expected rejections from a failed run.

`prover` separately measures 30 fresh Node processes and 30 warm proofs after an excluded warm-up. It verifies every proof. These are server timings, not laptop/phone UX. Avoid concurrent CPU-intensive jobs when collecting publication results. [The browser harness](browser/BENCHMARKING.md) provides the corresponding physical-device procedure; actual browser/mobile measurements remain pending.

```sh
npm run browser
# Open http://127.0.0.1:8765 on the same machine, then run and export JSON.
```

## Execution and fee boundaries

- Hardhat 3.20.0 / EDR: L1 runtime **Osaka**, OP Stack runtime **Isthmus**. The same Solidity 0.8.37 compiler, optimizer 200 and portable Cancun-target bytecode are used in both. Compiler target and execution hardfork are separate recorded choices.
- These are local execution environments, not forked production state, live transactions or a production load test. No real funds are used.
- Gas is read from actual successful transaction receipts. First-holder state, warmed holder state, cache hits, cache reauthorization, deployments, approvals and authenticated root updates are separate events.
- L2 execution gas alone is not the full transaction fee. L1 data charges, compression, oracle state and operator fees must be measured separately before a total L1/L2 cost claim.
- `results/fee_snapshot.json` contains observed fee-history summaries and a hash of the full compressed raw archive. The distribution of within-block median effective fees is **not** the distribution of all transactions. Sensitivity levels remain separately marked as assumptions.

## Earlier architecture accounting

The retained earlier architecture accounting uses 96 workload contexts. The current policy accounting and its workload assumptions are described in [POLICIES.md](POLICIES.md). Four architectures and two local chain runtimes are evaluations of those contexts, not hundreds of independent experiments. Access count is total across services. Cache misses follow an ordered trace of expiry and global registry changes. Credential lifetime and authorization TTL are separate. Issuance is reusable in both families; refresh-driven root publication, fixed deployment, population allocation and cache reauthorization are visible components.

The comparison conditions on a **common mixed registry**. A minimal standalone signed-credential system need not incur the same Merkle-root infrastructure. Synthetic token deployment/bootstrap costs are disclosed separately. Unknown issuer charges, witness distribution costs, user costs and full L2 fees remain unknown rather than zero. Alpha only distributes a specified invoice; it does not change total system cost or establish demand.

The useful question is whether saved repeated verification outweighs first-registration/storage and reauthorization costs under a stated workload. Do not infer universal ZK cost savings, a demand curve, willingness to pay, GDPR savings or optimal community policy from these gas measurements alone.

## Verification and remaining work

See `results/test_results.json`, [CIRCUIT_REVIEW.md](CIRCUIT_REVIEW.md), [STATIC_REVIEW.md](STATIC_REVIEW.md) and [REVIEW_RESPONSE.md](REVIEW_RESPONSE.md). Tests cover valid authorization, context binding/replay, current roots, predicates, activation/expiry boundaries, revocation, policy/issuer changes, and token failure/reentry rollback.

The phase-1 transcript is public and hash-pinned. Two phase-2 contributions come from **one local process**; they are not independent and the resulting keys are not production-safe. A production ceremony, operational issuer/witness service, physical-device measurements and full L2 fees are release/research gaps. A signature-inside-circuit treatment and proof-system comparisons are separate follow-up experiments, not features claimed by this version.
