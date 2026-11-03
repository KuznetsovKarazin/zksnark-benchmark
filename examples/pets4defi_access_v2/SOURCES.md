# Evidence and parameter provenance

Reviewed on 2026-10-20. These sources justify protocol semantics and the
measurement procedure; they do not turn illustrative parameters into observed
market data. Pin source/software versions and retain measured output with any
published result.

## Fee observations

Run the optional standard-library collector from this directory:

```sh
python3 scripts/collect_fees.py --expected-date 2026-10-20
```

For a later run, supply that run's UTC date or omit the explicit date guard.
The collector still rejects a head older than one hour or more than five minutes
in the future relative to its clock. This command collects the latest pinned
block window; it does not retrieve a historical window for the date argument.

Default read-only endpoints:

| Network | Chain ID | Endpoint | Endpoint provenance |
| --- | --- | --- | --- |
| Ethereum mainnet | 1 | `https://ethereum-rpc.publicnode.com` | [PublicNode provider page](https://ethereum.publicnode.com/) |
| OP Mainnet | 10 | `https://mainnet.optimism.io` | [Official OP connection information](https://docs.optimism.io/op-mainnet/network-information/connecting-to-op) |

Override an endpoint through `ETH_RPC_URL` or `OP_RPC_URL`. Endpoint credentials,
query values and arbitrary provider paths are redacted from output. There are
no API keys in this example. OP's public RPC is rate limited. The collector
does not use the write-only sequencer endpoint.

Only `eth_chainId`, `eth_getBlockByNumber`, and `eth_feeHistory` are allowed.
The archive includes request times, chain ID, the first/last block numbers,
hashes and UTC timestamps, raw fee-history responses, and per-block base fees,
priority-fee percentiles 10/50/90, and gas-used ratios. It uses at most eight
history calls of at most 1,024 blocks per network. A pinned final block is
rechecked to detect a reorganization during collection.

There are at most 7,200 consecutive blocks: approximately 24 hours on Ethereum
and four hours on OP. The measured boundary timestamp span, not those
approximations, describes the actual window. Individual block timestamps are
not fetched or invented. No automatic retries or endpoint spraying occur.

Metric definitions:

- [Ethereum execution API: `eth_feeHistory`](https://ethereum.github.io/execution-apis/api/methods/eth_feeHistory/)
  defines the RPC result and arrays. The extra final base-fee entry concerns the
  next block, so it is retained in the raw response but excluded from summaries.
- [Geth fee-history implementation documentation](https://pkg.go.dev/github.com/ethereum/go-ethereum/eth/gasprice#Oracle.FeeHistory)
  describes rewards as effective priority-fee percentiles within each block,
  weighted by transaction gas used. They are not unweighted transaction-price
  percentiles.
- [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559)
  distinguishes base fee and effective priority fee. For a nonempty block,
  adding its base fee to a reward percentile yields the corresponding
  within-block effective **execution** gas-price percentile. An individual
  transaction's execution fee is `gasUsed * effectiveGasPrice` from its receipt.
- The collector's p10/p50/p90 summary is a **block-weighted distribution of the
  within-block effective p50 values**, using nearest-rank quantiles. It is not
  a global transaction percentile or a globally gas-weighted percentile.
  Empty blocks remain in the archive/base-fee summary but are excluded from
  effective-price summaries because they have no transaction-price observation.
- [OP execution specification](https://specs.optimism.io/protocol/isthmus/exec-engine.html)
  includes separate L1 data and operator fees. The collected OP execution prices
  omit those components; they cannot alone price an OP transaction. Deposits and
  system transactions also make an OP aggregate different from a quote for a
  normal user transaction. Use a transaction-specific L1/operator fee estimator
  and receipts before asserting total L2 savings.

[`results/fee_snapshot.json`](results/fee_snapshot.json) is the compact summary:
it retains status, methodology, source metadata, observation windows and summary
statistics, plus the raw archive's relative path and SHA-256. The complete
snapshot, including every raw response and per-block observation, is retained
losslessly in [`results/fee_history_raw.json.gz`](results/fee_history_raw.json.gz).
The collector writes both files automatically. Gzip uses an empty embedded
filename and `mtime=0`; identical input produces an identical compressed archive.
The summary also records the uncompressed JSON's SHA-256. Verify the compressed
file against `raw_archive.sha256` before using its observations.

The summary records `available`, `partial`, or `unavailable`.
Transport failures, inconsistent dates/chain IDs, missing rewards and invalid
windows are explicit failures. Successful partial raw responses may be retained
as evidence, but they are not accepted observations. The process exits with
code 2 unless every requested network is available. Never replace a failed
collection with synthetic observations.

The externally suggested **0.067 and 0.38 gwei** values have not been independently
confirmed with a timestamp, window and metric. They are not calibration inputs
here. A current snapshot would not retroactively verify an undated claim.

### Archived observation from this run

This is a fresh recovery collection started on 2026-10-20 at 17:10:31 UTC.
The earlier local raw archive was lost before publication; this replacement is
a new observation, not a reconstruction of that earlier window. Collection
succeeded for both networks, with 7,200 consecutive blocks and eight history
requests each. The Ethereum window is 2026-10-19 17:05:11 through
2026-10-20 17:10:35 UTC (blocks 26228002–26235201).
The OP window is 2026-10-20 13:12:53 through 17:12:51 UTC (blocks
158451598–158458797). These are different-duration windows, not a matched-window
chain comparison. Boundary hashes were rechecked before accepting the archive.

| Metric (gwei) | p10 | p50 | p90 |
| --- | ---: | ---: | ---: |
| Ethereum block base fees | 0.040837022 | 0.102421391 | 0.459951361 |
| Ethereum distribution of within-block effective p50 | 0.050009874 | 0.130658648 | 0.716536567 |
| OP distribution of within-block execution-price p50 proxy | 0.000003638 | 0.000006661 | 0.000201975 |

Each block has equal weight in this table. OP values exclude L1 data/operator
fees and are not a total user-cost comparison. See the full raw responses and
decimal-wei observations in `results/fee_history_raw.json.gz`; use the exact window
when quoting these values. No fallback observations were substituted into this
successful recovery archive. Its compressed SHA-256 is
`3a34c0fa39e5fc1c14c72e8f1d2caa3b182e6e88b3463b8c470c41918e9d228a`.

## Ethereum fork and signature verification

- [Ethereum Foundation Pectra announcement](https://blog.ethereum.org/2025/04/23/pectra-mainnet):
  mainnet activation scheduled for 2025-05-07.
- [Official Fusaka overview](https://ethereum.org/roadmap/fusaka/): activation
  2025-12-03; includes the P-256 precompile. It does not claim direct reductions
  in L1 gas prices. Record the execution client's version and fork for gas tests.
- [EIP-7951](https://eips.ethereum.org/EIPS/eip-7951): `P256VERIFY`, address
  `0x100`, costs 6,900 gas for the precompile operation. This is not a complete
  transaction or ZK-proof price. It does not make ECDSA verification inside an
  arithmetic circuit free.
- [Official Ganache repository](https://github.com/Consensys-archive/ganache):
  archived 2024-02-26. A pinned Ganache reproduction can describe historical
  results; it does not establish current-fork gas results.

## Credentials, reuse and privacy

- [W3C Verifiable Credentials Data Model 2.0](https://www.w3.org/TR/vc-data-model-2.0/):
  validity properties and credential status are distinct. There is no universal
  90-day lifetime or 45-day remaining-lifetime rule.
- [Privado on-chain overview](https://docs.privado.id/docs/verifier/on-chain-verification/overview/)
  and [tutorial](https://docs.privado.id/docs/verifier/on-chain-verification/tutorial/):
  verification status can be stored and reused. A later `isVerified` check by
  itself is not evidence that expiry/revocation has been revalidated at that
  time. Test the pinned contracts' invalidation/freshness behavior. The tutorial's
  published gas numbers are explicitly from January 2024, not measurements of
  this example.
- [Semaphore glossary](https://docs.semaphore.pse.dev/glossary): nullifiers
  prevent repeated signaling within a scope; relaying is a separate issue.
  Membership privacy does not automatically hide the Ethereum sender or
  transaction/network metadata. An access nullifier, credential lifetime and
  proof/authorization freshness are different mechanisms.
- [Official EUDI ZKP technical specification](https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/blob/main/docs/technical-specifications/ts4-zkp.md):
  discusses ZKP integration, existing credential formats and implementation
  constraints. P-256 support alone does not establish interoperability with
  EUDI credentials or legal compliance.

## Public powers-of-tau provenance

The [iden3/snarkjs README](https://github.com/iden3/snarkjs/blob/master/README.md)
publishes a prepared BN128 powers-of-tau file for power 14 (maximum 16,384
constraints). The current README links:

`https://circom.info/powersOfTau28_hez_final_14.ptau`

Older README/package snapshots link the mirror:

`https://storage.googleapis.com/zkevm/ptau/powersOfTau28_hez_final_14.ptau`

The published **BLAKE2b-512** digest is:

```text
eeefbcf7c3803b523c94112023c7ff89558f9b8e0cf5d6cdcba3ade60f168af4a181c9c21774b94fbae6c90411995f7d854d02ebd93fb66043dbb06f17a831c1
```

Do not label this digest SHA-256. Verify the file against the published digest
and run `snarkjs powersoftau verify` before use. A successful download alone is
not validation. A local SHA-256 may additionally be recorded for artifact
provenance, clearly distinguished from the published BLAKE2b digest. A public
phase-1 transcript does not eliminate Groth16's circuit-specific phase-2 setup
requirements or make a demonstration setup production-ready.
