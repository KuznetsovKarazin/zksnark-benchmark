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

See [Protocol deviations and cohort sensitivity](#protocol-deviations-and-cohort-sensitivity) and the [manuscript section](sensitivity/manuscript_access.tex) for the change in data collection, activity selection and storage.

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

## Protocol deviations and cohort sensitivity

The 17 November protocol specified a single Dune query returning aggregate bins and counts. Wallet-specific sessions were outside its scope. That query returned HTTP 402. The subsequent exploratory analysis retrieved public Aave v3 Base Supply and Withdraw logs by RPC and reconstructed the sequence for each beneficiary or withdrawal owner. This changed the collection method, the unit of analysis and the estimand. It allowed actual access times to be replayed across hypothetical cache policies. It did not supply issuer affiliation. This change followed the Dune failure and was not prespecified in the original protocol.

The request spanned 180 days. The observed Aave window comprises 58 consecutive UTC days from 8 September through 4 November 2026 inclusive. This was the longest complete run returned by the provider. No gap crossed a missing day. The replay used the 14,440 addresses with at least three distinct transactions out of 42,739 observed addresses. Boundaries censor interarrival times. Web PKI remains a separate sensitivity using retained effective dates in signed CRL snapshots.

Locally cached rows contain the public beneficiary/owner, transaction hash and timestamp. The audit retains them outside Git. Since 18 November the retained access and code caches use owner-only directories and files (0700/0600). The original fallback used ordinary local file permissions. Raw paths and historical-code lookup tables are excluded from the shared results. The chain node receives individual public addresses for historical bytecode lookups. No EAS recipient matching is performed. The original protocol specified no deletion date. Public outputs contain cohort counts, aggregate intervals, policy totals and block-level provenance.

The initial [18 November cohort choices](sensitivity/ANALYSIS_PLAN.md) were committed before the subgroup costs were computed. The subsequent whole-path analysis was specified after those costs were available. Empty bytecode at the closing block is a proxy for a conventional EOA. A delegated EIP-7702 account, another account with code and a failed lookup have distinct statuses. Code state can change and empty-code accounts can be automated. Each 10/25/50 cap excludes wallets exceeding that number of transactions on any UTC day. Activity quartiles are defined across all eligible wallets and keep ties together. The full [manuscript text and findings](sensitivity/manuscript_access.tex), [interval table](results/aave_activity_cohorts.csv) and [paired policy table](results/aave_cohort_frontier.csv) document the sensitivity.

All 14,440 historical lookups succeeded at closing Base block 53,523,726. There were 9,998 empty accounts, 3,060 EIP-7702 designations and 1,382 other code-bearing accounts. Across the full cohort, 77.13% of pooled gaps were below one hour. The mean of the within-wallet fractions was 38.40%. Only 393 addresses exceeded ten transactions on a UTC day. These addresses supplied 72.06% of eligible accesses. Their removal lowered the pooled short-gap fraction to 35.15%. Within the 9,832 empty-code addresses also satisfying the cap, the fraction was 38.20%. Short gaps, code and high frequency do not establish whether an account is human-operated.

At F = 1 hour, the common-minus-selective increment per wallet was 2.66 for all eligible addresses, 1.33 for empty code, 1.17 under the daily cap of ten and 0.93 when both restrictions applied. For the intermittent issuer alone the increment fell from 5.32 to 1.86. The four transaction-count strata were exactly three, four, five to eight and nine or more. Their corresponding increments were 0.20, 0.31, 0.73 and 10.76 proofs per wallet. The direction persists with a substantially smaller magnitude in the restricted cohort.

Switching between the two hypothetical EAS schedules under selective publication changed the cache decision on 21.18%, 11.45% and 6.80% of observed accesses at F = 1, 6 and 24 hours. Equal weighting of wallets gives 21.95%, 17.33% and 13.03%. Pooled and equal-wallet weighting differ most at the longer deadlines. In both shared policies the matched decisions agree by construction. These event-level measures describe local differences. The [whole-path table](results/aave_path_frontier.csv) additionally gives the count of distinguishable paths, equal-prior accuracy and exact expected accuracy with 10% independent label errors for all nonempty cohorts and policies. Only G = 1 and G = 2 are supported by the two measured schedules. See the [access-sensitivity figure](../figures/aave_access_sensitivity.pdf).

In every published cohort and at each of the three deadlines, the intermittent-source full-proof decisions were a subset of the daily-source decisions, and the shared policy matched the daily-source total. At F = 1 hour all 76,810 disagreements point in the same direction. In this dataset the pooled disagreement fraction can therefore be recovered from the difference in full-proof counts divided by accesses. It supplies no independent validation of issuer-identification accuracy.

## Scientific review and frozen whole-path frontier

The primary result uses empty closing-block bytecode and a whole-wallet cap of ten accesses per UTC day. At a one-hour freshness ceiling, 5,560 of 9,832 eligible paths (56.55%) produced different sequences under the two selective source schedules. With equally likely sources, expected forced-choice accuracy was 78.28% under perfect labels and 74.01% with independent 10% label errors. A shared epoch and fixed batch both gave 50% in this channel. The shared epoch increased holder proof demand from 3.73 to 4.66 full proofs per wallet over 58 days. Its increment for the intermittent source alone was 1.86 proofs. The daily source incurred zero additional proofs in this comparison.

Use the [paired figure](../figures/aave_path_frontier.pdf) and [cohort and policy table](results/aave_path_frontier.csv) for the paper. With 14,440 paths in the full cohort the corresponding incremental cost for the intermittent source was 5.32. In the highest activity quartile it reached 21.52. Treat the full-cohort estimate as a reference for sample composition. The window covers 58 days and two update schedules. The assignments, cache labels, publication lag and label errors are modeled. No actual wallet affiliation was observed. The result concerns the cache/full-proof channel alone.

The matched-freshness contribution is the joint movement of resource use and conditional observability when choosing an issuer epoch. PUB-01 supplies background on timing and gas spillovers. ECON-07 and Economic Note v0.3.1 provide the earlier financing and allocation baselines. Registry operation, membership, actual fee incidence and monetary transfers are separate inputs for WP6. Web PKI remains a sensitivity. Results with more than two sources and positive selective clustering at 10,000 holders remain simulation evidence. NEXT-01 stays outside this paper. The numeric freeze covers the 18 November tables for the two-source replay.

## Base mainnet price replay

The release uses matched noon blocks from the original 90-day window, bracketing canonical headers and the historical Base GasPriceOracle getL1Fee call on a fixed unsigned EIP-1559 envelope. The historical base fee times local measured gas gives L2 execution at zero priority tip. The historical L1 quotation uses the same block. Nonce, gas cap, fee bytes, payload class and selected local transaction are explicit in fee_payloads.mjs and results/quote_templates.json. Freshness prices assume these call shapes and a fixed price scenario on each date. The replay does not reconstruct actual user invoices. For contract variants with different calldata and execution costs, retain the corresponding measured template or leave the fee unknown.

All eight quotations succeeded on 49 of the 90 dates. Median paired total fees were 1.7495 microETH for the selected full proof, 0.3383 microETH for the cache hit and 2.9244 microETH for all four independent publications in an empty period. Across the 58-day real-access cohort at F=1 h, median holder access cost was 16.57 microETH under equal-weight selective and 20.32 microETH under common. Registry operation is separate. Full group costs require deployed payer counts, publication mechanism and off-chain witness/settlement costs. These numbers price the two named Base fee components; optional tips or additional regime-specific charges would require separate evidence.

## Independent issuer updates

A repeated deterministic local root publicly discloses equality. The prototype gives each issuer its own authenticated slot and refreshes a reserved dummy leaf with a private 192-bit random value for every period, including empty periods. The public signer and fixed schedule remain visible. The local root changes in every honest period. The remaining 1,023 leaves are available for credentials. The registry combines the four authenticated roots on-chain only after all four arrive. Genesis and recovery use the same rule. A single issuer can still misstate credentials in its own subtree. All issuers must serve fresh witnesses. Compromised signing keys, predictable padding, timing beyond the agreed slot and colluding or observable witness services require separate analysis. This is an experimental implementation with no formal indistinguishability proof.

The local run checked nine conditions and verified an actual Groth16 membership proof with the earlier verification key. It records four update legs per complete epoch, their public calldata and measured gas. One empty epoch used 584,105 gas and the observed one-revocation epoch 584,081. These are two measurements; random calldata can change gas slightly. The fourth transaction finalizes the shared state and has a different cost from the first three. A missed signature holds the prior root until expiry and the service then fails closed.

## Observation controls and economic assignment

Five independently generated common-epoch datasets for each of four and 64 arbitrary issuer labels were used as negative controls. Each clustering run has 1,000 synthetic rows. A separate 1,000-event logging calibration estimates noise and missingness without the test labels. The common-epoch HMM was checked on 32 held-out paths per seed with a nonuniform prior. Maximum posterior drift was below 4e-16. Null ARI lay close to zero. These checks quantify spurious structure under the defense. The earlier 10,000-holder selective study still has one seed per size; positive-case accuracy under estimated noise is unverified.

The 18 November replication adds five independent seeds for each of four and 64 arbitrary labels at 10,000 synthetic paths per dataset. The ten common-epoch adjusted Rand indices range from -0.00018 to 0.00013. The maximum posterior drift on the synthetic negative control is 3.33e-16. The public [per-seed results](results/null_controls_10000.csv) retain every run. Positive-case selective clustering at this scale still has one published seed per size.

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
