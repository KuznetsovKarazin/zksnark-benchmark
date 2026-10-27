# Measured results: PETs4DeFi v2

Recorded: 2026-10-20T15:02:11.063Z. Source revision: `cb39a2afcc881651aee424e02d465bf3f8361303`.
Exact measured source-file hashes: `results/measurements.json`. Debug run: **False**.

Integration/assertion checks: **784 passed, 0 failed** across the two runtimes.
These counts include assertions, negative cases and state invariants; they are not independent security audits.

## Receipt gas

Medians; brackets show IQR. First-holder registration/access is one observation; recurring rows have 30 observations in the main run.

| Chain / treatment | First access or registration | Recurring direct access / cache hit | Cache reauthorization |
|---|---:|---:|---:|
| l1 / signed_direct | 117,020.0 [0.0]; n=1 | 82,832.0 [0.0]; n=30 | — |
| l1 / signed_cache | 168,442.0 [0.0]; n=1 | 66,762.0 [0.0]; n=30 | 100,054.0 [0.0]; n=30 |
| l1 / zk_direct | 376,082.0 [0.0]; n=1 | 321,713.0 [12.0]; n=30 | — |
| l1 / zk_cache | 445,367.0 [0.0]; n=1 | 66,762.0 [0.0]; n=30 | 336,934.0 [21.0]; n=30 |
| op / signed_direct | 117,044.0 [0.0]; n=1 | 82,856.0 [0.0]; n=30 | — |
| op / signed_cache | 168,466.0 [0.0]; n=1 | 66,762.0 [0.0]; n=30 | 100,078.0 [0.0]; n=30 |
| op / zk_direct | 376,082.0 [0.0]; n=1 | 321,725.0 [21.0]; n=30 | — |
| op / zk_cache | 445,391.0 [0.0]; n=1 | 66,762.0 [0.0]; n=30 | 336,922.0 [12.0]; n=30 |

Both chains are local simulations. OP rows exclude L1 data and operator fees. Gas equality does not imply equal transaction prices.

## Effect of status updates

Example projection: 100 total accesses, one app, 1,000 users, 90-day credential, 30-day cache TTL, 90-day horizon. Includes separately recorded demo setup and registry costs allocated over users. This is a trace calculation, not a population benchmark.

| Root-change workload | Treatment | Full authorizations | Cache hits | Known execution gas / user |
|---|---|---:|---:|---:|
| none | signed_direct | 100 | 0 | 8,370,429.3 |
| none | signed_cache | 3 | 97 | 6,897,505.3 |
| none | zk_direct | 100 | 0 | 32,279,595.1 |
| none | zk_cache | 3 | 97 | 7,648,664.7 |
| weekly | signed_direct | 100 | 0 | 8,375,081.5 |
| weekly | signed_cache | 13 | 87 | 7,235,077.6 |
| weekly | zk_direct | 100 | 0 | 32,284,247.4 |
| weekly | zk_cache | 13 | 87 | 10,354,965.0 |
| daily | signed_direct | 100 | 0 | 8,404,933.6 |
| daily | signed_cache | 90 | 10 | 9,828,413.6 |
| daily | zk_direct | 100 | 0 | 32,314,099.4 |
| daily | zk_cache | 90 | 10 | 31,187,506.6 |
| population_unbatched | signed_direct | 100 | 0 | 8,758,118.3 |
| population_unbatched | signed_cache | 100 | 0 | 10,514,518.3 |
| population_unbatched | zk_direct | 100 | 0 | 32,667,284.1 |
| population_unbatched | zk_cache | 100 | 0 | 34,242,339.3 |

This common-registry comparison charges the shared root workload to both families. It is not a minimal signed-only deployment cost. Unknown service, witness distribution and user costs are not set to zero.

## Server prover evidence

AMD EPYC 9V74 80-Core Processor; v24.19.0; single-thread fullProve; default snarkjs verification; sequential samples.

| Measurement | n | Median ms | IQR ms |
|---|---:|---:|---:|
| cold_proof_ms | 30 | 1,884.9 | 73.3 |
| cold_process_wall_ms | 30 | 2,357.9 | 90.6 |
| warm_proof_ms | 30 | 1,849.5 | 90.8 |

Fresh Node process for each proof. OS filesystem cache is not flushed; this is not cold hardware or browser startup.
fullProve includes witness generation and artifact reads; excludes separate verification and process startup

**Browser and physical phone: unmeasured.** The executable harness is provided; server numbers must not be relabelled as mobile performance.

## Evidence and interpretation

- `measurements.json`: environment, setup provenance, exact source hashes and successful gas events.
- `raw_ci_node24.zip`: complete successful CI artifact, including raw `transactions.json`; `ci_provenance.json` ties the archive to the tested merge and source head.
- `proof_samples.json`, `test_results.json`: verified proof timings and checks from that same CI run.
- `fee_snapshot.json` / `fee_history_raw.json.gz`: timestamped public fee evidence and raw RPC archive.
- `architecture_results.csv`, `trace_counts.csv`, `break_even.csv`: inspectable state-trace accounting. All CSVs, including the larger `trace_events.csv` and price conversions, are in `economic_tables.zip` with a checksum manifest.
- `server_prover.json` / `server_setup.json`: separate local 30-run cold/warm measurement, with its own environment and setup hashes; it is not the CI prover dataset.
- `price_inputs.csv`: missing prices and fee components; assumed stresses and observed fee conversions are distinct.

Read THREAT_MODEL.md and REVIEW_RESPONSE.md before using these numbers in an article. The result is a reproducible architecture experiment with limited privacy properties, not a production system or completed empirical cost–privacy frontier.
