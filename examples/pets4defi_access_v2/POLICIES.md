# Access policies: experiment protocol

## Question and controls

Measure the cost of a private eligibility presentation under a specified cache and status-freshness policy. Five methods share token-transfer, nonce, balance accounting and reentrancy behavior: unchecked deposit, signed direct/cache, and ZK direct/cache. The unchecked control isolates eligibility overhead; the matched ZK-minus-signed difference isolates the on-chain privacy premium.

User transaction gas, application deployment and registry-operator work are separate budgets. The mixed registry is not an optimized standalone signed deployment. Common infrastructure must not be counted repeatedly in system comparisons.

## Policy semantics

| Policy | Signed cache | ZK cache | Ordinary revocation Δ | Old-root grace τ |
|---|---|---|---:|---:|
| global | Any publication invalidates | Any publication invalidates | 0 s | 0 s |
| security | Own issuer/ID/policy status | Security epoch changes invalidate | 0 s | 300 s |
| delay_300 | Own status, bounded delay | First invalidation + Δ | 300 s | 300 s |
| delay_3600 | Own status, bounded delay | First invalidation + Δ | 3,600 s | 300 s |

Credential expiry and authorization expiry always apply. Issuer disablement and policy changes are emergency invalidations with no delay. Selective signed caches do not depend on unrelated Merkle-root changes. `revokePublic` changes only signed-ID status; `revokeAndPublish` atomically changes the public-ID status and the hidden active-set representation. The issuer must publish the correct root.

A root replaced by an addition remains presentable for τ. A root invalidated by revocation is additionally limited by Δ, measured from its security epoch's **first** invalidation. Stale-proof authorization preserves that old epoch and cannot renew the deadline. Root grace bounds presentation, not existing cache life. Thus Δ=3,600 and τ=300 permit at most 300 seconds for an old-root direct proof, versus up to 3,600 seconds for an existing cached authorization. Configured freshness upper bounds are comparable; actual presentation windows are not identical across all methods.

The registry trusts an issuer's addition-only classification: an opaque Merkle root does not prove append-only behavior. Removal/replacement uses a security update. Delays are research settings, not assertions of legally acceptable revocation latency.

## Measurement

`npm run policy` compiles the three policy contracts against the unchanged 7,409-constraint circuit and executes the local Osaka EVM with Solidity 0.8.37, optimizer 200, Cancun-target bytecode. It uses the locked dependencies and hash-checked setup artifacts.

Recurring operations have 30 samples. First-holder events and deployments are single observations. The synthetic fixture is small; a population allocation is an economic scenario, not a load test. Actual batches change eight credential leaves of one issuer before publishing one root. Separate publications perform the corresponding leaf changes individually. Root reconstruction is off-chain; the on-chain registry reconstructs the four-issuer aggregate. Renewal replacement publications are classified as security changes.

Successful transaction receipts, included-revert receipts, proofs, setup hashes, source hashes and named assertion results are retained. Static-call preflight rejection has no chain gas; computation, witness refresh and waiting may still be wasted. Measured failure costs do not estimate a network failure frequency. Reproof timing is a server observation, not phone performance.

## Accounting and uncertainty

`policy_economics.py` applies measured event costs to explicit, ordered synthetic workloads. Primary tables use batched renewals. Unbatched renewals remain a sensitivity calculation. The focused burst trace makes minute-scale Δ effects observable; evenly spaced quarterly accesses cannot establish a general latency/cost frontier.

The revoked-credential exposure calculation is distinct from the cost trace of an unaffected legitimate user. Denied access is not counted as a cheap successful deposit. No incident probability or monetary loss is invented.

The Ethereum fee snapshot is archived and hash checked. Its block-weighted distribution of within-block median effective fees supplies price scenarios, not percentiles of quarterly user bills. €2,170/ETH is an assumption. Full L2 fees, issuer and witness-service prices, physical-device timings, demand and risk valuation remain unknown.

## Reproduction and evidence

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
