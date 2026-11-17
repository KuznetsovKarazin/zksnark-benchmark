# Figure interpretation

Both figures use the 80-case synthetic daily model (128 holders per run, 20
independent seeds). Noise parameters and activity probability are known to the
attacker. Rates differ across issuers; the displayed panels use uniform issuer
priors and issuer-independent access probabilities. Errors are independent.
These are not real-chain identification rates.

`hmm_robustness`: all displayed cells were run; color and labels give final-day
accuracy. Seed-level Student-t 95% intervals are in `summary.csv`. Identification
with posterior >= 0.95 is a different metric, available in the result files.

`cost_observability`: error bars are 95% intervals across seed means. The x-axis
is a proof-count cost proxy, not money or measured L2 fees. A seven-day batching
period additionally needs ingestion/publication/finality lag L in its freshness
budget. Common/batch preserve the prior in this channel; this does not prove
privacy against auxiliary information, address linkage or service-side signals.
