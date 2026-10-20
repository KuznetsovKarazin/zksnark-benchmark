# Measured eligibility-access policies

The policy experiment passed 1249 named assertions and 22 accounting tests. It records 976 measured events and 29 included reverted transactions. Recurring events have 30 observations; first-holder events and deployments are single observations.

Measurement source: `1d7e7cfcbb8a50d2dfc6fb891aa8f173ad186e75`; measured source files were clean. Exact file/setup hashes, environment and receipts are retained.

## Starting workload

100 total deposits, one service, 1,000 users split across four issuers, 90-day credentials, 30-day authorization TTL, daily additions and weekly unrelated revocations; selective security invalidation. These are synthetic workload assumptions.

| Method | User transaction gas / 90 days | Full authorizations | Cache hits |
|---|---:|---:|---:|
| unchecked | 5,556,651.0 | 0 | 0 |
| signed_direct | 8,401,951.0 | 100 | 0 |
| signed_cache | 8,847,173.0 | 3 | 97 |
| zk_direct | 33,301,917.2 | 100 | 0 |
| zk_cache | 11,584,657.8 | 13 | 87 |

The cached ZK-minus-signed user cost is approximately €0.776 at the archived fee-p50 scenario and €4.256 at fee-p90, assuming €2,170/ETH. Direct verification gives approximately €7.060 and €38.717. These are partial-cost price scenarios, not quarterly bill percentiles. Setup, operator publications and unknown off-chain prices are separate.

In some no-revocation/monthly selective-cache contexts the user-gas difference is slightly negative. The signed cache reads individual credential status on each access, while the ZK cache uses a security epoch. Preserve this implementation-specific result; it does not establish lower whole-system ZK cost.

## Interpretation

The global policy deliberately invalidates on additions; selective policies avoid that coupling. Ordinary revocation uses the first invalidation time. A cached authorization cannot be renewed past that time plus Δ by presenting an old proof. Emergency changes invalidate immediately. Root-presentation grace is separate: the direct Δ=3,600-second comparison is explicitly flagged because old ZK roots have a 300-second presentation limit.

Actual eight-leaf batching is measured. The economic population uses four replacement roots per renewal round; the alternative unbatched projection uses 1,000. Neither executes a 1,000-user production system. The burst example isolates minute-scale revocation delay and keeps an unaffected user’s cost distinct from a revoked credential’s exposure.

## Reproduction and retained evidence

Run `npm ci && npm run policy` in this directory, then `python3 scripts/package_policy_results.py`. The participant tables are regenerated from the measured events; unknown input-register values are preserved.

- [Policy protocol](POLICIES.md) and [participant task](../../projects/pets4defi/README.md).
- [Measurements](results/policy_measurements.json), [assertions](results/policy_tests.json) and [accounting provenance](results/policy_accounting_summary.json).
- [Complete evidence archive](results/policy_evidence.zip) with byte-preserved receipts, proofs, traces, verifier and accounting tables; [manifest and hashes](results/policy_evidence_manifest.json).

Limits remain: trusted issuer classification of additions, synthetic eligibility/credentials/token, local L1 execution, same-process demonstration phase 2, unknown issuer/witness prices, physical-device performance, real failure frequency and full L2 fees.
