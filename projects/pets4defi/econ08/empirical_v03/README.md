# ECON-08 empirical extension v0.3

Research implementation for the 17 November 2026 extension proposal. This is a
separate extension of `econ08-native-pilot` at
`004fa70891b466a95c78572eb8354a400b3fb1db`; it does not change PUB-01 or its results.

## What the evidence means

1. EAS attesters are already public. Combining their historical revocation times
   with independently sampled DeFi access histories is a **trace-driven
   counterfactual**, not an observed attack on a deployed private-eligibility
   service. No EAS-recipient/DeFi-wallet linkage is inferred.
2. `config/protocol.json` fixes the 90-day window (19 August inclusive to
   17 November 2026 exclusive, UTC). The feasibility gate requires four attesters
   with at least ten distinct revocation days each, plus 1,000 on-chain
   attestations before the window end. Indexer pagination, chain coverage and
   successful qualification are different checks. An unavailable range is unknown,
   never zero. On-chain and off-chain attestations are not pooled.
3. The exact HMM uses a declared daily Bernoulli-access model. Its hidden state
   includes issuer, cache age and pending invalidation. Missing actual full
   accesses reset the hidden cache even when the observer sees no transaction.
   This model does not preserve continuous-time DeFi sessions. `replay.py` is a
   separate continuous-time, noiseless, complete-access experiment and resamples
   whole wallet paths, retaining calendar alignment and bursts.
4. Independent simulation seeds provide Monte Carlo uncertainty conditional on
   the model/window. They are not independent real-world temporal replications.
   Never-identified holders are right-censored; their event times are not set to
   90 days as if identification occurred. The conditional median is labeled.
5. Spectral clustering produces unlabeled groups. ARI/AMI are not named-issuer
   identification. The optional anchor experiment excludes disclosed anchors from
   accuracy evaluation and reports coverage. A weak attack's failure is not a
   privacy proof. A consistently relabeled issuer permutation is an invariance
   test, not a null control; an independent truth permutation is a null.

## Implemented components

| Component | Location | Scope |
|---|---|---|
| Resumable RPC acquisition | `src/acquire.py` | Explicit block ranges, source hashes, deduplication, reorg/hash checks, timestamp enrichment |
| EAS feasibility screen | `src/indexer_gate.py` | Cursor pagination, off-chain exclusion, separate aggregate count, errors retained |
| Log normalization | `src/traces.py` | Aave beneficiary and Compound source/destination semantics; duplicate address/transaction logs removed |
| Counterfactual replay | `src/replay.py` | Stops unless input gate is chain-validated PASS |
| Exact noisy observer | `src/observers.py` | Forward HMM with missed-call marginalization; sparse kNN spectral attack and anchors |
| Stress runner | `src/experiment.py` | 4/8/16/32/64 issuers, 0–20% label error, 0–30% missing calls, nonuniform rates and priors |
| Public-only extractor | `examples/pets4defi_access_v2/scripts/empirical/extractor.mjs` | Transaction/receipt/header consistency, selectors plus events, reverted/unknown calls, explicit fee gaps |
| Batched registry | `examples/pets4defi_access_v2/contracts/BatchedPolicyRegistry.sol` | Unchanged four-issuer circuit and PolicyGate; combined-root publication and freshness expiry |
| Local/live harness | `examples/pets4defi_access_v2/scripts/empirical/evm_demo.mjs` | Real Groth16 proofs, 32/128 wallets, fixed-cadence update, cache/root boundary checks |

All `examples/...` paths in this table are relative to the repository root.

## Batched registry: assumptions and boundaries

The old registry publishes issuer indices and leaf roots and rejects unchanged
roots. Wrapping those calls in one transaction does not hide the publisher.
The new adapter accepts only a combined Poseidon root from a trusted coordinator.
No new ZK circuit is introduced; the on-chain circuit still has **four** slots.
The 8–64 issuer experiments are model experiments, not deployments of that circuit.
The existing credential tree also has 1,024 leaf slots per issuer; the
10,000-holder experiment is a model/clustering experiment, not that circuit's
on-chain capacity demonstration.

Deploy the adapter only with `PolicyGate(zkMode=true, cacheEnabled=true,
policyMode=1, deltaSeconds=0, rootGraceSeconds=0)`, as enforced by the harness.
Mode 0 bypasses the freshness callback and is unsupported. Signed mode is also
unsupported. This adapter is an experimental component, not an audited product.

The coordinator must ingest complete issuer changes, correctly compute the root
and provide private membership witnesses. The contract cannot verify those
off-chain duties. An unchanged root can be published as a heartbeat and still
advances the cache epoch. A missed heartbeat eventually fails closed.
With period P and a publication/ingestion/finality bound L, the acceptance
deadline is cutoff + P + L; there is no extra cache or root grace. Thus a required
freshness F needs P + L <= F. The contract enforces acceptance deadlines, not
upstream completeness or network liveness. A delay exactly L is allowed; stale
acceptance ends strictly at its deadline.

A public upstream source such as EAS still reveals its attester. Common periodic
cache invalidation removes an issuer-specific refresh response in the modeled
channel, but cannot erase the source's public identity, external anchors, wallet
linkability, witness-delivery timing or revocation of the holder's own credential.
Grouping exposes the group and reduces the anonymity set. Rate-based grouping is
a hypothesis to test, not a proven optimal policy. Full-proof counts depend on
occupied access periods and TTL; they are not generally 90/P.

## Reproduce

From the repository root, install NumPy, SciPy and scikit-learn in a Python
environment, then:

```sh
python -m unittest discover -s projects/pets4defi/econ08/empirical_v03/src -p 'test_*.py' -v
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python projects/pets4defi/econ08/empirical_v03/src/experiment.py --out /tmp/econ08-stress --seeds 20
```

The optional `--scale` adds two 10,000-holder sparse-clustering cases (one seed
each). These demonstrate execution at that size; they are not confidence
intervals or a complete 10,000-holder HMM sweep. Run expensive jobs sequentially.

Additional reproducible studies:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python projects/pets4defi/econ08/empirical_v03/src/run_ofat.py --out /tmp/econ08-ofat1000
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python projects/pets4defi/econ08/empirical_v03/src/calibrated.py --calibration-file projects/pets4defi/econ08/empirical_v03/results/calibrated/calibration.json --out /tmp/econ08-calibrated --holders 1000
```

The second command uses two measured source profiles to construct explicitly
synthetic surrogate issuers. It does not bypass the failed four-real-issuer gate.

```sh
cd examples/pets4defi_access_v2
npm ci --ignore-scripts --no-audit --no-fund
npm run setup
node scripts/empirical/validate_archives.mjs
node scripts/empirical/evm_demo.mjs --holders=32
node scripts/empirical/evm_demo.mjs --holders=128
node scripts/empirical/preflight.mjs
node scripts/empirical/verify_release.mjs
```

Setup verifies the pinned public phase-1 transcript, but phase 2 is a local
demonstration setup, **not production-safe**. The local harness uses real proofs
and EVM execution, but local execution is not public-testnet evidence.

For an explicitly funded disposable Base Sepolia or OP Sepolia signer, configure
`ECON08_TESTNET_RPC` and `ECON08_TESTNET_PRIVATE_KEY` locally, then run the same
harness with `--broadcast --holders=32`. Never paste a secret into a conversation
or commit it. Only chain IDs 84532 and 11155420 are allowed. The default funding
cap is 0.05 testETH. Live tests use real time and may need a longer `--period` and
`--lag` for slow RPC/proof generation. The live run is a functional demonstration,
not a 90-day empirical replay. Ephemeral test wallets stay in memory.

Testnet receipts measure gas and testETH charges, not observed euro or mainnet
prices. OP-chain fee totals may include execution, L1 data and fork-dependent
operator fees. Unknown components remain null. No EUR conversion is inferred.

For acquisition, keep `--out` / `--private-out` outside the repository:

```sh
python projects/pets4defi/econ08/empirical_v03/src/acquire.py eas_base --out /private/econ08 --enrich
python projects/pets4defi/econ08/empirical_v03/src/acquire.py compound_base --out /private/econ08 --enrich
python projects/pets4defi/econ08/empirical_v03/src/indexer_gate.py --private-out /private/econ08-indexer --summary /tmp/data_gate.json
```

The acquisition module also supports Ethereum/Optimism EAS and Aave on Base.
Publish aggregates, manifests and hashes. Do not publish live address/issuer
tables or private credentials. Retain counts of excluded one- and two-access
addresses and do not equate contract addresses with individual users.

## Corrections to the proposal

The earlier 13-to-4 result means **69.23% fewer full authorizations** and
**24.43% less modeled gas**. These percentages are not interchangeable.
The weekly formula E[R] = 4 + 9 rho is specific to the earlier schedule/access
scenario. It is not a theorem for empirical traces.

The strongest publication package is an explicit attack surface, a successful
public-data extractor, trace-driven evidence with honest coverage, and an
implementable cost/freshness/observability trade-off. A larger synthetic grid
alone does not remove the external-validity limitation.

## Primary sources

- EAS contracts: https://docs.attest.org/docs/quick--start/contracts
- EAS API: https://docs.attest.org/docs/developer-tools/api
- Coinbase Verifications: https://github.com/coinbase/verifications
- Aave event interface: https://github.com/aave/aave-v3-core/blob/master/contracts/interfaces/IPool.sol
- Aave deployments: https://github.com/aave-dao/aave-address-book/blob/main/src/AaveV3Base.sol
- Compound events: https://github.com/compound-finance/comet/blob/main/contracts/CometMainInterface.sol
- Compound Base deployment: https://github.com/compound-finance/comet/blob/main/deployments/base/usdc/roots.json
- OP transaction fees: https://docs.optimism.io/op-stack/transactions/fees

See `STATUS.md` and `results/` for the checks actually completed; implemented
commands are not themselves evidence that a public deployment or data gate passed.
