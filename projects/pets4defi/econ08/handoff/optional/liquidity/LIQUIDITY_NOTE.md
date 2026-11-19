# Timed liquidity diagnostic on existing traces

ECON-07 + ECON-08 v0.4, 13 November 2026. **Optional; for information only.**

The scientific gate remains open. Applying the fixed [SELF/PM rules](../../FINANCING_RULES.md) to eight archived traces does not establish a new full-lifecycle funding effect. This is new accounting of existing EVM observations, not a new EVM experiment or a measured paymaster implementation.

## Evidence and primary result

The input contains 3,390 included gas-debit records from N=16, A=4, HIGH, δ=0, B1/B2/B4/signed, each with weekly publications and a matched no-update control. Every run includes four initial holder approvals and 400 accesses. Shared operator and issuer costs are separate. Source hashes and event times are retained in [trace_inputs.json](trace_inputs.json).

The common origin is the fixture initialization before setup. For every rule and grouping, initial funding occurs there and refills reset balances to their fixed targets on the same clock, before same-time operations. Refills are ideal, free and instantaneous in this spending-floor diagnostic. No customer receipts or reimbursements are assumed. Historical prices are q0=0.130658648 gwei and EUR/ETH=2164.73.

Across the six ZK weekly/control traces, the daily holder-pool target is 2,313,044–2,313,152 gas (about EUR 0.6542 for all four holders). The seven-day target is 3,935,684–3,935,792 gas (about EUR 1.1132). Both maxima occur in the first interval. The 108-gas range is not evidence of a meaningful liquidity effect; its cause is not isolated by this diagnostic. The sum of the four SELF holder targets equals the PM pool target in every supplied case, so these traces do not establish a pooling advantage.

These are hindsight lower bounds from actual debits, not transaction-admission reserves, UserOperation prefunds or safe deployment balances. Validation gas limits, fee caps, bundles, account-abstraction overhead, refill fees/delay and price uncertainty are unmeasured. Shared expenses and their separate account targets remain visible in [liquidity_accounts.csv](liquidity_accounts.csv).

## Secondary description, not a replacement target

The fixed secondary daily statistic omits only the first calendar interval `[t0,t0+24h)` and takes the maximum across all later daily windows. No event is moved; no cached state, TTL phase or authorization expense is reset. All full-lifecycle expenses remain in the primary result.

| Grouping | Weekly updates: later daily maximum, gas | No updates: later daily maximum, gas |
|---|---:|---:|
| B1 | 1,693,460 | 1,411,784 |
| B2 | 1,117,194 | 1,411,844 |
| B4 | 829,043 | 1,411,832 |

Later expenditure can differ in either direction because actual renewal and expiry phases differ. These descriptive differences do not alter the startup-dominated full-lifecycle target. Seven-day secondary results use their own first seven-day cutoff and are labelled separately in [liquidity_summary.csv](liquidity_summary.csv).

Without refills or receipts, the required actual-debit floor equals cumulative spending. That equality is an accounting control, not evidence of a burst. Deposits and top-ups are transfers. The account table reports initial transfer, later top-ups, total treasury funding and ending balance separately, with `gross funding − resource expense = ending balance`. An unused balance remains an asset.

## Next predeclared study and stop rule

Before extending the workload, specify whether startup is separately funded and how continuing service begins. Compare matched access and TTL phases under the same refill clock, retain the full-lifecycle result and report both positive and negative effects. Test realistic refill delay, fees and validation reserves when the required inputs exist. Do not select a phase or sponsor cap solely to force a reversal or a positive finding.

A standard or familiar payment rule does not automatically pass G0a. If the result remains a rescaling or restatement of prior cost/TTL findings, revise the article's claim before commissioning the new A=32 EVM family. Longer-grace EVM changes, own-holder revocation/reissuance and A64 remain deferred.

## Reproduce this accounting only

Run these from this optional directory; no blockchain or proving setup is needed:

```sh
python3 -m unittest -v test_liquidity_diagnostic.py
python3 liquidity_diagnostic.py --out /tmp/econ08_liquidity_replay
```

The supplied calculation passed nine accounting and boundary tests. [liquidity_results.json](liquidity_results.json) records limitations and reference prices. To rebuild the extracted inputs from the original receipts, use `extract_trace_inputs.py --repo /path/to/repository --out /tmp/econ08_trace_inputs.json`; that optional provenance step requires the separate source repository. Nataliya is not asked to run these commands.
