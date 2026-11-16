# Historical reference prices

These are the existing ECON-07/08 conversion references, not new market quotes.
The included source snapshots are copied unchanged from research commit
`ca1fabbb1d2fb777adca87544e689a14f6b5fbdb`.

* [Gas snapshot](price_source_fee_snapshot.json): Ethereum, 7,200 blocks,
  19 October 2026 17:05:11 UTC to 20 October 2026 17:10:35 UTC.
  `networks[0].summary.within_block_effective_p50_block_weighted.p50_wei`
  is 130,658,648 wei/gas = 0.130658648 gwei/gas. This is the block-weighted
  median of within-block effective p50 values, not a global transaction percentile.
* [FX snapshot](price_source_fx_quote.json): 2,164.73 EUR/ETH, dated 20 October
  2026. Observed dated web quote; retrieval time is not a market tick or daily close.

The x10 and x100 scenarios change gas price only; the ETH/EUR conversion stays
fixed. These sensitivities are neither forecasts nor historical quantiles.
EUR/gas = gas price in gwei × 10^-9 × EUR/ETH.

For the weekly example the access-only premium is 2,593,251 gas per holder,
or EUR 0.7334769154 at this reference. Compensation changes who pays it, not the
amount of gas consumed. No new L2 total-fee model or paymaster overhead is supplied.

Original sources at the pinned repository snapshot:

https://github.com/KuznetsovKarazin/zksnark-benchmark/blob/ca1fabbb1d2fb777adca87544e689a14f6b5fbdb/examples/pets4defi_access_v2/results/fee_snapshot.json

https://github.com/KuznetsovKarazin/zksnark-benchmark/blob/ca1fabbb1d2fb777adca87544e689a14f6b5fbdb/projects/pets4defi/data/fx_quote.json
