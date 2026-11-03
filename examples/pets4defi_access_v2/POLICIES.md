# Access policies: experiment protocol

## Question and controls

Measure the cost of a private eligibility presentation under a specified access and status-freshness policy. Five methods share token-transfer, nonce, balance accounting and reentrancy behavior: unchecked deposit, signed direct/cache, and ZK direct/cache. The unchecked control measures eligibility overhead. The primary decision compares the minimum user-transaction gas among signed modes with the minimum among ZK modes, under the same workload and freshness requirements.

Direct-to-direct and cache-to-cache differences are matched implementation controls, retained in `results/policy_comparisons.csv`. They are not the primary selection rule: a favorable comparison with a dominated signed mode does not establish a lower cost than the best signed option. `results/policy_decisions.csv` records the selected modes and their difference.

User transaction gas, application deployment and registry-operator work are separate budgets. Mode selection minimizes action and approval gas only; it is not a whole-system optimum. Issuer and witness services, user computation and expected failure costs remain separate unknowns. The mixed registry is not an optimized standalone signed deployment. Common infrastructure must not be counted repeatedly in system comparisons.

## Policy semantics

| Policy | Signed cache | ZK cache | Ordinary revocation Δ | Old-root grace τ |
|---|---|---|---:|---:|
| global | Any publication invalidates | Any publication invalidates | 0 s | 0 s |
| security | Own issuer/ID/policy status | Security epoch changes invalidate | 0 s | 300 s |
| delay_300 | Own status, bounded delay | First invalidation + Δ | 300 s | 300 s |
| delay_3600 | Own status, bounded delay | First invalidation + Δ | 3,600 s | 300 s |

Credential expiry and authorization expiry always apply. Issuer disablement and policy changes are emergency invalidations with no delay. Selective signed caches do not depend on unrelated Merkle-root changes. `revokePublic` changes only signed-ID status; `revokeAndPublish` atomically changes the public-ID status and the hidden active-set representation. The issuer must publish the correct root.

A root replaced by an addition remains presentable for τ. A root invalidated by revocation is additionally limited by Δ, measured from its security epoch's **first** invalidation. Stale-proof authorization preserves that old epoch and cannot renew the deadline. Root grace bounds presentation, not existing cache life. Thus Δ=3,600 and τ=300 permit at most 300 seconds for an old-root direct proof, versus up to 3,600 seconds for an existing cached authorization. Configured freshness upper bounds are comparable; actual presentation windows are not identical across all methods.

The registry trusts an issuer's addition-only classification: an opaque Merkle root does not prove append-only behavior. Removal/replacement uses a security update. A shared security epoch invalidates ZK authorization after unrelated removals; this is an architectural choice, not an unavoidable cost of private credentials. Different status structures would require their own measurements. Delays are research settings, not assertions of legally acceptable revocation latency.

## Measurement

`npm run policy` compiles the three policy contracts against the unchanged 7,409-constraint circuit and executes the local Osaka EVM with Solidity 0.8.37, optimizer 200, Cancun-target bytecode. It uses the locked dependencies and hash-checked setup artifacts.

Recurring operations have 30 samples. Current-epoch cache hits and accepted old-epoch ZK cache hits are measured separately; the latter read the original invalidation deadline without refreshing authorization. Cache access reads only the required stored fields. First-holder events and deployments are single observations. The synthetic fixture is small; a population allocation is an economic scenario, not a load test. Actual batches change eight credential leaves of one issuer before publishing one root. Separate publications perform the corresponding leaf changes individually. Root reconstruction is off-chain; the on-chain registry reconstructs the four-issuer aggregate. Renewal replacement publications are classified as security changes.

Successful transaction receipts, included-revert receipts, proofs, setup hashes, source hashes and named assertion results are retained. Static-call preflight rejection has no chain gas; computation, witness refresh and waiting may still be wasted. Measured failure costs do not estimate a network failure frequency. Reproof timing is a server observation, not phone performance.

## Accounting and uncertainty

`policy_economics.py` applies measured event costs to explicit, ordered synthetic workloads. The model population is split across four issuers with 250 cohort credentials each. Daily single-leaf additions rotate between issuers; synchronized renewals replace expired slots and publish four roots per round. Primary tables use batched renewals and the immediate-revocation `global` and `security` policies: 120 method rows and 24 decisions. Unbatched renewals remain a technical sensitivity calculation.

The main monthly schedule places revocations at days 30 and 60, aligned with the 30-day authorization TTL. It is an explicit control, not evidence of a generally negligible monthly-revocation cost. `phase_sensitivity.csv` fixes two revocations while changing their positions to days 15/45, 30/60 or 37/67, using `security`, 90-day credentials and one or five services. These are finite two-event schedules, not samples from an observed population. Phase effects must not be confused with changes in revocation frequency.

The quarterly workload has evenly spaced accesses, 0.9 days apart. The bounded-delay variants can therefore have identical authorization counts even though their security exposure differs. Minute-scale delays are examined separately in the eight-row focused burst table. It measures a conditional mechanism through counts of authorizations and cache hits; its selected access/revocation times cannot establish an optimal Δ or a general latency/cost frontier. Small differences in separately measured event gas must not be interpreted as savings caused by a delay when event counts are unchanged.

The revoked-credential exposure calculation is distinct from the cost trace of an unaffected legitimate user. Denied access is not counted as a cheap successful deposit. Empirical revocation frequency, temporal clustering and access timing are required to calibrate the workload. No incident probability, demand or monetary loss is invented. The direct Δ=3,600 comparison remains a diagnostic with unequal maximum presentation windows; it is excluded from the primary decision table.

The Ethereum fee snapshot is archived and hash checked. Its block-weighted distribution of within-block median effective fees supplies price scenarios, not percentiles of quarterly user bills. EUR conversions use the recorded CoinGecko quote of €2,164.73/ETH on 20 October 2026; `projects/pets4defi/data/fx_quote.json` records its source and time. The fee window and exchange-rate observation are separate inputs, not an observed quarterly bill. Full L2 fees, issuer and witness-service prices, physical-device timings, demand and risk valuation remain unknown.

## Reproduction and evidence

[Measured results](POLICY_RESULTS.md) · [Complete evidence archive](results/policy_evidence.zip) · [Archive manifest](results/policy_evidence_manifest.json)

Raw receipt/proof JSON and long traces listed below are retained byte-for-byte in the archive.

```sh
npm ci
npm run policy
```

- `results/policy_measurements.json`: event gas and measurement/source metadata.
- `results/policy_tests.json`: positive, negative, deadline and rollback assertions.
- `results/policy_transactions.json`: raw successful/reverted receipts.
- `results/policy_proofs.json`: verified proof samples and server timings.
- `results/policy_artifacts/`: exact verifier, verification key and setup metadata.
- `results/policy_*.csv`: derived accounting and ordered traces.
- `projects/pets4defi/data/`: compact participant tables and provenance.

The local phase-2 setup has two contributions from one process; it is not an independent production ceremony. This is a research measurement fixture, not a deployable identity service.
