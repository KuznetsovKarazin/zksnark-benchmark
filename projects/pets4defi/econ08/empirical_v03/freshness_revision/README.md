# ECON-08 matched-freshness revision

A daily revocation source can transfer reauthorization costs to holders of an intermittent issuer. How much they pay depends on when they access the service. This revision uses actual access times, measures that transfer at fixed freshness and supplies an independently signed alternative. The figure and cost table are suitable for scientific review. Final WP6 accounting awaits the choice of implementation, payer population and cost boundaries.

## Research scope and the paper

PUB-01 studies revocation timing and gas spillovers. ECON-07 and Economic Note v0.3.1 study financing and the incidence of a given premium. The additional contribution here is the dependence of the cache response and proof demand on the grouping of issuers at the same maximum revocation age. A systems paper can present the design, counterfactual trace results and limitations. Historical q0 and the four-rule return retain their original denominators.

Protocol commit for the separate descriptive extension is [aeacd96](https://github.com/KuznetsovKarazin/zksnark-benchmark/commit/aeacd964755a66d15b20e28430594d4fe4677001). The overlapping 90 days were known before the new protocol. The live component and chain fees are separate. The public testnet is optional for this comparison.

## Equal freshness and operating cost

Every fixed-F panel compares policies with the same cutoff dates, lag and cold start. P equals F minus five minutes. For literal P = 1, 6 and 24 h, the modeled maximum ages are 65, 365 and 1,445 minutes. The 7-day control is retained only in the historical daily table. Its freshness cannot support any of these SLAs. L includes source ingestion, publication and required confirmation under the assumed service. No outage-free SLA has been measured.

The prompt reference in subdaily_summary.csv uses period_s=0 and a 300-second bounded feed. Select it for a comparison under the same ceiling, separately from the exact-cadence plots. The hard-silence variant requires empty authenticated freshness certificates for event-driven groups. The ledger reports these separately from state changes and assumes such certificates do not invalidate caches. Their gas depends on a concrete certificate implementation. Registry writes are system totals. Proofs and hits are holder costs.

The new figure's vertical coordinate is the fraction of matched issuer switches that change a full/cached decision. For each fixed access, path and random cover draw, k of B possible issuers require a proof. The ordinate averages 2k(B-k)/(B(B-1)) over accesses for a uniform ordered pair of distinct issuers. It describes how the mechanism responds. It cannot be read as the probability of successful identification. The previous HMM figure keeps its own longitudinal metric.

The calibrated daily control reuses the v0.3 simulator and random stream. All three old selective means reproduce. With both original profiles and 1,000 synthetic holders per seed, selective requires 27.77 full proofs on average. Common and daily batch require 40.49 out of 40.49 accesses. Among holders assigned to the intermittent source, the figures are 15.24 and 40.50. With four synthetic issuers selective reproduces 27.6725. The daily activity rule allows only one access per holder per UTC day.

For the subdaily model, public hourly counts come from the original two Base attesters. Within-hour times are synthetic. The 16-issuer case duplicates and shifts their templates. The paired path set contains 256 holder schedules per seed. Each path is evaluated under every possible source. Compare daily Bernoulli single accesses against a sensitivity with pairs 20 minutes apart and half the active-day probability. TTL is 30 days. The release includes 216 cases times 20 seeds and 320 daily-control rows. G denotes issuers per group. Rate-matched grouping uses the known template class as an idealized design choice. Random and rate-matched groups share all other draws. Treat overlap of plotted points as an empirical property of the workload.

For 16 model issuers, paired sessions and F = 1 h, the mean proof counts are 19.27 for selective, 22.70 for groups of four like-rate issuers, 27.57 for random groups of four and 27.70 for common or fixed batch. The corresponding response-disagreement rates are about 26.3%, 14.6%, 0.5% and 0%. Equal-rate grouping reduces work while preserving a more distinctive cache response. The optimum therefore depends on the privacy and freshness objectives.

## Observed data and counterfactual proof costs

During the original 90 days, the dominant Base source contributes 22,969 of 23,125 indexed Base revocations. Its 1,232,657 attestations are a cumulative pre-cutoff count. Dividing yields 1.863%, an event-to-cumulative-issuance ratio. Estimation of a 90-day cohort hazard would require at-risk counts, issuance cohorts, expiries and observation-time handling.

The 180-day indexer screen returned 50,115 revocations on Base. The same two individually qualifying profiles were found: 49,731 revocations on 180 days and 126 on 31 days. Ethereum returned 15, Optimism 38, Arbitrum One 4 and Linea EAS 0 through its available index. An indexer's latest issuance is an activity timestamp and does not certify indexing completeness. Scroll pagination and both published Verax Linea endpoints did not supply complete coverage. Missing ranges are unknown. Independence of legal entities is not implied by differing addresses. The original four-source, 90-day screen is unchanged.

Dune returned HTTP 402 to one bounded aggregate request. Independent retrieval of Base Aave v3 Pool Supply/Withdraw events covered 58 consecutive days, September 8 through November 4 inclusive, out of 180 requested. The provider supplied all requested ranges in this span. It was selected by availability, before computing interval statistics. All failed days remain in the public coverage table. The matched analysis ignores intervals crossing a missing day. It checks each completed day's endpoint timestamps and an interior event's block hash, deduplicates wallet/transaction pairs, uses the supply beneficiary or withdrawal owner, and combines neither EAS recipients nor Aave wallets across sources.

The span contains 440,979 events, 400,766 wallet/transaction pairs and 42,739 distinct addresses. Counts by observed accesses are 18,488 once, 9,811 twice and 14,440 at least three times. The last group contributes 362,656 accesses and 348,216 adjacent intervals. Of these intervals, 2,282 share a timestamp and 266,295 have a positive duration under one hour. The sample includes automation and contract wallets. In-window gaps are conditionally observed, with censoring at both ends. Applying the two source histories to each eligible path with equal weights gives the following counts per wallet over 58 days.

| Maximum age F | Batch period | Selective | Common epoch | Fixed batch |
|---|---|---:|---:|---:|
| 1 hour | 55 min | 5.72 | 8.38 | 8.39 |
| 6 hours | 5 h 55 min | 4.49 | 5.93 | 5.93 |
| 24 hours | 23 h 55 min | 3.91 | 4.76 | 4.76 |

Mean observed access count is 25.11. At literal P = 24 h, the intermittent source alone gives 3.09 proofs, versus 4.75 under a common epoch. A daily reset clears an earlier cache on each epoch change. Same-epoch accesses can still be hits. See results/trace_freshness.csv for the literal periods and the separate source columns. These exact-trace cutoffs use half-open event windows. The subdaily simulation assigns a synthetic event exactly at cutoff to that cutoff. The conventions are documented separately.

The CCADB inventory sampled one full-CRL URL for each of 46 catalogue owners among currently valid TLS-capable Mozilla-trusted intermediates with a disclosed full URL. Forty-four snapshots passed issuer-name, CA fingerprint and signature checks. Exclusions include indirect/CA-only CRLs and unavailable endpoints. They retain 12,548 entries with in-window effective revocation dates, with positive counts for 25 selected owners. Multiple endpoints, keys, cross-signs and shards do not by themselves establish independent CA operators. Historical publication cadence needs archived successive signed thisUpdate records with continuity. Single current CRLs have retention and expiry bias. CRLite filter updates also have their own redistribution cadence.

A secondary sensitivity used the 39 verified snapshots whose thisUpdate covered the end of the selected Aave span. Using only retained effective dates at a daily cutoff gave 1.88 selective, 4.56 common and 4.75 fixed-batch proofs per wallet. These are conditional stock-based inputs. EAS and Web PKI remain separate panels. Regenerating a later CRL snapshot can change these data. Original selected snapshot/certificate hashes and public endpoints are recorded.

## Base mainnet price replay

The release uses matched noon blocks from the original 90-day window, bracketing canonical headers and the historical Base GasPriceOracle getL1Fee call on a fixed unsigned EIP-1559 envelope. The historical base fee times local measured gas gives L2 execution at zero priority tip. The historical L1 quotation uses the same block. Nonce, gas cap, fee bytes, payload class and selected local transaction are explicit in fee_payloads.mjs and results/quote_templates.json. Freshness prices assume these call shapes and a fixed price scenario on each date. The replay does not reconstruct actual user invoices. For contract variants with different calldata and execution costs, retain the corresponding measured template or leave the fee unknown.

All eight quotations succeeded on 49 of the 90 dates. Median paired total fees were 1.7495 microETH for the selected full proof, 0.3383 microETH for the cache hit and 2.9244 microETH for all four independent publications in an empty period. Across the 58-day real-access cohort at F=1 h, median holder access cost was 16.57 microETH under equal-weight selective and 20.32 microETH under common. Registry operation is separate. Full group costs require deployed payer counts, publication mechanism and off-chain witness/settlement costs. These numbers price the two named Base fee components; optional tips or additional regime-specific charges would require separate evidence.

## Independent issuer updates

A repeated deterministic local root publicly discloses equality. The prototype gives each issuer its own authenticated slot and refreshes a reserved dummy leaf with a private 192-bit random value for every period, including empty periods. The public signer and fixed schedule remain visible. The local root changes in every honest period. The remaining 1,023 leaves are available for credentials. The registry combines the four authenticated roots on-chain only after all four arrive. Genesis and recovery use the same rule. A single issuer can still misstate credentials in its own subtree. All issuers must serve fresh witnesses. Compromised signing keys, predictable padding, timing beyond the agreed slot and colluding or observable witness services require separate analysis. This is an experimental implementation with no formal indistinguishability proof.

The local run checked nine conditions and verified an actual Groth16 membership proof with the earlier verification key. It records four update legs per complete epoch, their public calldata and measured gas. One empty epoch used 584,105 gas and the observed one-revocation epoch 584,081. These are two measurements; random calldata can change gas slightly. The fourth transaction finalizes the shared state and has a different cost from the first three. A missed signature holds the prior root until expiry and the service then fails closed.

## Observation controls and economic assignment

Five independently generated common-epoch datasets for each of four and 64 arbitrary issuer labels were used as negative controls. Each clustering run has 1,000 synthetic rows. A separate 1,000-event logging calibration estimates noise and missingness without the test labels. The common-epoch HMM was checked on 32 held-out paths per seed with a nonuniform prior. Maximum posterior drift was below 4e-16. Null ARI lay close to zero. These checks quantify spurious structure under the defense. The earlier 10,000-holder selective study still has one seed per size; positive-case accuracy under estimated noise is unverified.

Nataliya's current assignment is the literature/background and a symbolic heterogeneous-issuer externality note with the four established rules. The numerical WP6 price and allocation table follows the scientific scope and frontier freeze. Her standalone aggregate is results/base_daily_counts.csv.

## Reproduction

From this directory, use the Python dependencies pinned by empirical_v03, and cryptography for CRL signature checks. The deterministic public arithmetic audit uses only the Python standard library. Raw access records and live identifiers are never part of the published packet.

```sh
python check_release.py
python daily_controls.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python frontier.py
python plot_costs.py
python price_replay.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python negative_controls.py
```

For live-source acquisition, keep the following cache directories private.

```sh
python extended_sources.py --private-dir /tmp/econ08-eas180
python verax_screen.py
python pki_snapshot.py --cache /tmp/econ08-pki
python aave_rpc.py --private-dir /tmp/econ08-aave
python trace_costs.py --private-aave /tmp/econ08-aave
python historical_fees.py
```

The previous 90-day Base export can be converted to public hourly and exact slot counts with prepare_eas_aggregates.py. From examples/pets4defi_access_v2, install the locked Node dependencies, run the existing local setup, and execute node scripts/empirical/independent_epochs.mjs. The public checksum manifest pins the observed run; random padding and the local proving setup yield different byte values on a new run.

Primary sources: [Base fees](https://docs.base.org/specifications/transactions/network-fees), [OP predeploy specification](https://specs.optimism.io/protocol/predeploys.html), [Aave v3 event interface](https://github.com/aave/aave-v3-core/blob/master/contracts/interfaces/IPool.sol), [EAS](https://docs.attest.org/docs/developer-tools/api), [Verax](https://docs.ver.ax/developer-guides/using-the-subgraph), [Dune SQL](https://docs.dune.com/api-reference/executions/endpoint/execute-sql), [CCADB](https://www.ccadb.org/resources), [RFC 5280](https://www.rfc-editor.org/rfc/rfc5280), [Mozilla CRLite](https://hacks.mozilla.org/2025/08/crlite-fast-private-and-comprehensive-certificate-revocation-checking-in-firefox/), [Liu et al., IMC 2015](https://www.securepki.org/imc15.html).
