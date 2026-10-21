# Economic interpretation — recovered CI evidence

This note was recomputed from the current `architecture_results.csv`,
`break_even.csv` and `trace_counts.csv`. Primary evidence is the successful
[Node 24 CI run](https://github.com/KuznetsovKarazin/zksnark-benchmark/actions/runs/39443693715),
testing merge `cb39a2afcc881651aee424e02d465bf3f8361303` with head
`13bd6e58e7d4f6f6c55df8ec07ee4a1c34b5024a`. The recorded benchmark source
files match that head. Metadata records `source_dirty=false`,
`debug_run=false`, 30 warm samples per repeated event and chain, 468 event
records and 784 passing integration/security checks.

Current `measurements.json` SHA256:
`45753cc9c06d00125d9f776adebb5fa81a0e1fb9d0f24c2540dea5e84cc41ca3`.
This note uses the recovered CI values, not the earlier local-run values.

## What the comparison establishes

On **each** local chain, among 96 modeled workload contexts:

| Comparison | Exact count |
|---|---:|
| Signed direct has the lowest known execution gas | 78 / 96 |
| Signed cache has the lowest known execution gas | 18 / 96 |
| ZK cache beats signed direct | 4 / 96 |
| ZK cache beats signed cache | 0 / 96 |

ZK direct also never beats signed direct. These counts describe the selected
grid; they are not market frequencies or probabilities. The result supports
studying the cost of the specified ZK authorization and the conditions for
cache reuse. It does not establish that ZK is generally cheaper or that every
privacy property is better than a matched signed eligibility credential.

## Favorable workload and sensitivity to root changes

All figures below are **known execution gas per person for the entire 90-day
horizon**, in millions, rounded to three decimals. The workload is 100 total
accesses, one app, 1,000 users sharing setup, credential validity 90 days and
authorization TTL 30 days. Each architecture issues one initial credential
per person. These L1 projections include allocated demonstrator setup and
shared registry updates; unknown issuer/prover charges are excluded.

| Background root updates | Signed direct | Signed cache | ZK direct | ZK cache | Cache reauthorizations / hits |
|---|---:|---:|---:|---:|---:|
| None | 8.370 | 6.898 | 32.280 | 7.649 | 2 / 97 |
| Weekly | 8.375 | 7.235 | 32.284 | 10.355 | 12 / 87 |
| Daily | 8.405 | 9.828 | 32.314 | 31.188 | 89 / 10 |
| One unbatched update per population member | 8.758 | 10.515 | 32.667 | 34.242 | 99 / 0 |

In the no-background case, the exact L1 totals are 8,370,429.273,
6,897,505.285, 32,279,595.101 and 7,648,664.713 gas respectively. There is one
initial cached authorization, two reauthorizations and 97 hits; cache
authorization bundles the deposit. The 30-day authorization TTL explains why
some reauthorizations remain even without background updates.

Caching reduces known execution gas by **17.60%** for signed credentials and
**76.30%** for ZK against their respective direct paths. ZK cache is **8.62%**
below signed direct, but still **10.89% above signed cache**. The matched
cache baseline is essential: much of the saving comes from avoiding repeated
authorization, an optimization available to both credential designs.

The OP execution-gas ranking is the same. Its exact no-background totals are
8,372,829.273, 6,897,577.285, 32,280,505.901 and 7,648,666.313 gas. These
figures do not include OP L1 data or operator fees.

## Conditional cache thresholds

For the workload above, let r be the number of reauthorizations after initial
registration. Using the current CI L1 measurements:

- Signed cache beats signed direct when
  `r * 33,292 < 1,539,507.988`: at most **46** reauthorizations.
- ZK cache beats ZK direct when
  `r * 270,164.8 < 25,171,259.988`: at most **93** reauthorizations.
- ZK cache beats signed direct only when
  `r * 270,164.8 < 1,262,094.160`: at most **4** reauthorizations.

Daily updates produce 89 reauthorizations: signed caching loses its advantage,
while ZK caching retains a small advantage over ZK direct. The population
case produces 99 reauthorizations and zero hits: both cached designs cost more
than their own direct alternatives. Higher population can therefore lower
setup cost per person while also increasing invalidation in the
population-dependent churn scenario. A threshold against signed direct does
not establish an advantage over the cheaper matched signed-cache design.

## Use and limits

These are gas-only comparisons conditional on a **common mixed registry**.
A standalone signed service need not pay for the same Merkle-root mechanism
and requires its own matched measurements. Population renewal is synchronized
and unbatched; workloads and update schedules are modeling assumptions. Setup
includes mock-token and bootstrap components, separately identified in the
CSV. No full monetary cost, profit, adoption or optimal user share is claimed.

Use `architecture_results.csv` and `break_even.csv` for mechanism comparisons,
`trace_events.csv` for cache invalidation, and fee tables only for explicitly
labeled price conversion. Check issuer invoices for overlap with counted
root-publication gas. The five alpha allocation rules redistribute a cost
pool; they do not reduce its resource use or establish willingness to pay.

The independent review verified all 768 architecture rows against the current
raw-measurement hash, action-count conservation, component sums and setup/
update amortization. The recovered tables contain 96 traces and 384 matched
break-even comparisons. No accounting discrepancy was found.
