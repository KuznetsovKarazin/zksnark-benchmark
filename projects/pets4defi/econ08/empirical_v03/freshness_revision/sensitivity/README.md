# Reproducing the Aave access sensitivity

The fixed 58-day window spans 8 September to 4 November 2026 inclusive. The descriptive study requested 180 days. The private inputs are needed only to regenerate the aggregates. The public consistency checks and the figure use no wallet records.

From the matched-freshness directory run the following commands. The working example uses a dedicated owner-only folder outside the repository for the original Aave day files and the historical-code cache.

```sh
install -d -m 700 /tmp/econ08-review-private
python aave_rpc.py --private-dir /tmp/econ08-review-private/aave
python sensitivity/historical_code.py --private-aave /tmp/econ08-review-private/aave --private-code-cache /tmp/econ08-review-private/code.json
python sensitivity/cohorts.py --private-aave /tmp/econ08-review-private/aave --private-code-cache /tmp/econ08-review-private/code.json
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python negative_controls.py --clustering-n 10000
python sensitivity/check_tables.py
python sensitivity/plot_sensitivity.py
```

For an exact rerun, the coverage ledger and the original 58 daily inputs must agree on block range, hash and row count. A fresh network acquisition can differ in availability. Keep a separate checkout for fresh acquisition to preserve the frozen observations. Historical lookups use the closing block number, with the canonical block hash and two bytecode controls checked before and after lookup. Only status categories are cached. Subsequent runs retry unknowns.

The tables give both pooled and equal-wallet interval percentages. Policy comparisons use equal weights for the two hypothetical sources and the same observed paths and cutoffs. The public aggregate decision-disagreement rate describes the dependence of the mechanism on the source schedule. No per-wallet predictions or cache traces are released.

The large negative control has five separately seeded, issuer-independent datasets at each of two label counts. Positive-case clustering and longitudinal accuracy have a separate evidence base. See the [article section](manuscript_access.tex), [deviations statement](../README.md#protocol-deviations-and-cohort-sensitivity), [data collection and weighting plan](ANALYSIS_PLAN.md), [Ethereum execution API](https://ethereum.github.io/execution-apis/api/methods/eth_getCode/) and [EIP-7702](https://eips.ethereum.org/EIPS/eip-7702).
