# Measured eligibility-access policies

The policy experiment passed 1369 named assertions and 26 accounting tests. It records 1036 measured events and 29 included reverted transactions. Recurring events have 30 observations; first-holder events and deployments are single observations. Current-epoch and accepted old-epoch ZK cache hits are measured separately.

Measurement source: `8e71e52fbfef382b96b75266a7c78d816c7e1751`; measured source files were clean. Exact file/setup hashes, environment and receipts are retained.

## Starting workload

100 total deposits, one service, 1,000 users across four issuers, 90-day credentials, 30-day authorization TTL, daily additions and weekly unrelated revocations; selective security invalidation. These are synthetic workload assumptions.

| Method | User transaction gas / 90 days | Full authorizations | Cache hits |
|---|---:|---:|---:|
| unchecked | 5,556,651.0 | 0 | 0 |
| signed_direct | 8,401,951.0 | 100 | 0 |
| signed_cache | 8,227,440.0 | 3 | 97 |
| zk_direct | 33,301,917.2 | 100 | 0 |
| zk_cache | 10,661,616.6 | 13 | 87 |

The decision comparison selects **signed_cache** and **zk_cache**, the lowest user-transaction gas within each family for this workload. Their difference is **2,434,176.6 gas**, or approximately **€0.688** at the archived fee-p50 scenario and **€3.776** at fee-p90. Conversion uses the dated CoinGecko quote of €2,164.73/ETH on 20 October 2026. These are partial-cost price scenarios, not quarterly bill percentiles. Deployment, operator work and unknown off-chain prices do not enter this selection objective.

Signed selective cache hits cost 79,972 gas versus 83,213 for signed direct repeats. Cache registration and reauthorization also cost gas: the best signed mode is cache for this one-service workload, but direct for the five-service weekly workload. A cache is not automatically economical.

Without unrelated revocations, the same one-service comparison is -447,121.4 gas (about €-0.126 at fee-p50): ZK cache is cheaper even than the selected signed cache on this user-transaction boundary. Individual public-ID status reads and a shared hidden-status epoch have different access costs. Preserve this conditional negative result; it does not establish lower full-service ZK cost.

## Timing and interpretation

The participant workload has 120 rows for global/security policies and 24 minimum-family decisions. The coarse 0.9-day access spacing does not resolve 300/3,600-second delay effects. Full technical policy rows and matched access-mode comparisons remain available for diagnostics.

The main monthly control uses days 30/60, aligned with the authorization TTL. A separate 30-row phase table keeps two revocations fixed and compares days 15/45,30/60 and37/67. With 90-day credentials, shifting 30/60 to 37/67 changes ZK full authorizations from 3 to4 for one service, and 15 to20 for five services. This is timing sensitivity, not empirical revocation frequency.

In the focused burst, both positive delays need one reauthorization, versus five under immediate security invalidation. Their measured action costs are not exactly equal: the 300-second trace has six accepted old-epoch hits; the 3,600-second trace has nine, priced separately. The latter also allows 12 times the maximum revocation exposure. Neither trace establishes an optimal delay. Real inter-arrival times, clustering and access timing remain missing empirical inputs.

The ZK gate stores no public issuer/credential handle for selective invalidation, so this implementation conservatively invalidates caches using a shared security epoch. The resulting cost is conditional on that architecture, not a universal lower bound on private-credential cost. Emergency invalidation remains immediate. Old-root proof presentation grace differs from an existing cache's revocation-delay bound.

Actual eight-leaf batching is measured. The model allocates four replacement roots per renewal round; the unbatched sensitivity uses 1,000. These are population projections, not a 1,000-user execution test.

## Reproduction and retained evidence

Run `npm ci && npm run policy` in this directory, then `python3 scripts/package_policy_results.py`. The participant tables are regenerated from measured events and the dated FX snapshot; unknown input-register values are preserved.

- [Policy protocol](POLICIES.md) and [participant task](../../projects/pets4defi/README.md).
- [Measurements](results/policy_measurements.json), [assertions](results/policy_tests.json) and [accounting provenance](results/policy_accounting_summary.json).
- [Complete evidence archive](results/policy_evidence.zip) with byte-preserved receipts, proofs, traces, verifier and accounting tables; [manifest and hashes](results/policy_evidence_manifest.json).

Limits: trusted issuer classification of additions, synthetic eligibility/credentials/token, local L1 execution, same-process demonstration phase 2, unknown issuer/witness prices, physical-device performance, real failure frequency and full L2 fees. Scientific acceptance remains open.
