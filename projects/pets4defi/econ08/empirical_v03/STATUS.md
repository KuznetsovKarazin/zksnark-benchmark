# Verified status — 18 November 2026

The [matched-freshness revision](freshness_revision/README.md) supersedes the original cost figure. It includes the calibrated cache controls, grouping results, the independent issuer heartbeat prototype, and source coverage for the separate descriptive study.


| Work package | Executed evidence | Status and limit |
|---|---|---|
| Real EAS schedules | Complete indexer pagination: Ethereum 5, Base 23,125, Optimism 6 revocations in the frozen 90-day window | INDEXER_INSUFFICIENT: two qualifying source addresses, four required. Operator independence and full chain coverage remain unverified. |
| Real DeFi access paths | 58 contiguous Aave Base days, 8 September to 4 November 2026. Locally replayed 14,440 eligible active paths with two measured EAS schedules. | Exploratory RPC deviation from the Dune-only plan. Costs and aggregate cache-response sensitivity are available. Wallet-to-issuer identification accuracy is unmeasured. |
| Public-field extractor | 25 archived local runs; 15,346 transactions; 8,875 accesses; zero mismatches; seven negative checks | PASS for the archived cases |
| New batched-registry local demo | 32 wallets: 199 transactions, 97 accesses, 17 checks; 128 wallets: 775 transactions, 385 accesses, 19 checks | PASS on local EVM; four-issuer circuit unchanged |
| Independent proof verification | 322 Groth16 proofs independently verified from released public calldata; zero classification/gas mismatches | PASS; includes 32- and 128-wallet runs |
| Public testnet | Live-capable harness and bounded-spend preflight | NOT DEPLOYED: no funded signer configured; endpoint timed out |
| HMM robustness | 1,600 runs: 80 cases x 20 seeds x 128 holders | Complete; synthetic, daily-grid, known noise parameters |
| One-factor sensitivity | 300 runs: 15 cases x 20 seeds x 1,000 holders | Complete; synthetic |
| EAS-profile calibration | 60 runs: 4/16/64 synthetic issuers x 20 seeds x 1,000 holders | Complete; two fixed observed templates duplicated/shifted, synthetic accesses |
| Spectral scale | 10,000 simulated holders, 4 and 64 labels. The selective positive case has one seed per size. The five-seed common-epoch control is a separate experiment. | Only the selective scale check has been used in the original positive-case report. |
| Freshness | Delay computed on 23,136 indexed revocations for a period grid | L=300 seconds is an assumption, not measured network latency |
| Numerical audit | All 1,960 seed runs independently reaggregated; Student-t intervals checked | PASS |
| Python checks | 15 tests, including exhaustive hidden-history likelihood and decoder/freshness cases | PASS |

Selected robustness result: with 20% label error and 30% missed accesses,
the synthetic HMM achieves 89.92% final accuracy for four issuers and 54.84%
for 64 issuers. Seed-level 95% interval half-widths are 1.23 and 2.57 percentage
points. These are not measured identification rates for deployed users.

The 10,000-holder spectral cases produce ARI 0.9689 (four issuers) and 0.1244
(64 issuers). With 10% disclosed anchors, accuracy on the remaining holders
is 98.81% and 27.98%, respectively. Each is one synthetic seed.

The trusted coordinator can publish an invalid root. This adapter is not a
trust-preserving replacement for independent issuer authentication and is not
a production audit. Freshness protection requires ZK mode, policyMode 1,
zero delta, zero root grace, bounded L and P + L <= F.

The existing circuit supports four issuer slots and 1,024 credential leaves
per issuer. Experiments with 8–64 issuers or 10,000 holders are model studies,
not measurements of an enlarged circuit.

Initial independent GitHub check:
https://github.com/KuznetsovKarazin/zksnark-benchmark/actions/runs/44178264468
It reproduced the exact Base and Ethereum indexer revocation hashes, but
separate data-query errors kept its data gate UNKNOWN. Workflow success does
not mean the empirical gate passed. Local result/provenance files are the
source of the completed-run counts above; the final release workflow also
rechecks all published proof records and numerical summaries.

Raw live attester/UID data and incomplete real wallet paths are not included
in this public release. Aggregate daily calibration profiles, source hashes,
protocols, local-EVM public records and reproducible simulation outputs are
included. The public code and reports are in English.
