# Reproducing the Aave access sensitivity

The fixed 58-day window spans 8 September to 4 November 2026 inclusive. The descriptive study requested 180 days. The private inputs are needed only to regenerate the aggregates. The public consistency checks and the figure use no wallet records.

From the matched-freshness directory run the following commands. The working example uses a dedicated owner-only folder outside the repository for the original Aave day files and the historical-code cache.

```sh
install -d -m 700 /tmp/econ08-review-private
python aave_rpc.py --frozen-span --private-dir /tmp/econ08-review-private/aave
python sensitivity/historical_code.py --private-aave /tmp/econ08-review-private/aave --private-code-cache /tmp/econ08-review-private/code.json
python sensitivity/cohorts.py --private-aave /tmp/econ08-review-private/aave --private-code-cache /tmp/econ08-review-private/code.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python negative_controls.py --clustering-n 10000
python sensitivity/check_tables.py
python sensitivity/plot_sensitivity.py
python sensitivity/plot_path_frontier.py
```

The frozen-span option checks the published 58 ranges, both boundary block hashes, both event totals per day and the event counts. It leaves the existing 180-day coverage ledger in place. Archive availability can change. Historical lookups use the closing block number, with the canonical block hash and two bytecode controls checked before and after lookup. Only status categories are cached. Subsequent runs retry unknowns.

The tables give both pooled and equal-wallet interval percentages. Policy comparisons use equal weights for the two hypothetical sources and the same observed paths and cutoffs. The public aggregate decision-disagreement rate describes the dependence of the mechanism on the source schedule. No per-wallet predictions or cache traces are released.

## Whole-path outcomes

[The paired frontier](../results/aave_path_frontier.csv) gives one row for each nonempty cohort, freshness ceiling and policy. A path is distinguishable without noise if the two counterfactual cache decisions differ at least once. The `distinguishable_wallets` count is the numerator and `wallets` is its denominator. With equal source probabilities, a mandatory choice succeeds on all distinguishable paths and on half of the remaining paths in expectation. These endpoint probabilities describe a specified two-schedule model on real access times. The study has no observed user affiliation.

The noisy channel has two static hidden states, one per source, and an independent 0.10 probability of a reversed cache/full label at every access. All access times, publication times, cache rules, initial state and both hypothetical schedules are given. A label error affects the recorded label only. The cache follows the original policy. `accuracy_10pct` averages the conditional probability of a correct forced choice over the entire error distribution. Equal likelihoods receive half credit. The cohort calculation uses only a histogram of the number of differing decisions. No individual classifications are produced. This count-space evaluation is the exact reduction of the two-state HMM under these assumptions. Missing accesses, correlated label errors, unequal priors and hidden publication times require a different model.

The published columns pool counts into 0, 1–2, 3–4, 5–6, 7–8 and 9 or more differences. Adjacent odd/even pairs in this list have the same expected accuracy with ties split. For the last bin, `expected_correct_10pct_in_9_plus` gives the sum of the conditional success probabilities before pooling. It is measured in expected correct choices. The public validator checks cohort partitions, the forced-choice rates and both shared-policy controls, and verifies the channel probabilities against an independent forward probability sum.

The large negative control has five separately seeded, issuer-independent datasets at each of two label counts. Positive-case clustering and longitudinal accuracy have a separate evidence base. See the [article section](manuscript_access.tex), [deviations statement](../README.md#protocol-deviations-and-cohort-sensitivity), [data collection and weighting plan](ANALYSIS_PLAN.md), [Ethereum execution API](https://ethereum.github.io/execution-apis/api/methods/eth_getCode/) and [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702).
