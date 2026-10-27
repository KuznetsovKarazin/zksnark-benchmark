# V2 accounting: measured events and state traces

Run from this example directory:

```bash
python3 scripts/economics.py --measurements results/measurements.json --out results
python3 -m unittest discover -s scripts -p 'test_economics.py'
```

## What is compared

The four implementations are `signed_direct`, `signed_cache`, `zk_direct`, and
`zk_cache`. A credential is issued once per new user and is reusable across
applications. Neither signed variant is forced to repeat KYC for each app.
All variants use the same common mixed registry and its epoch schedule.
This is a conditional comparison inside that architecture, not a claim that a
minimal standalone signed-credential service requires a Merkle registry or
incurs the same root-publication costs. A standalone signed service could be
cheaper; it would need its own matched status measurements.

There are **96 primary workload contexts**:

- 1, 10, or 100 total accesses per user over `[0,90)` days;
- 1 or 5 deployed applications; visited applications = `min(apps, accesses)`;
- 10 or 1,000 users sharing fixed costs;
- credential validity of 30 or 90 days;
- no background updates, weekly updates, daily updates, or one unbatched
  background update per population member per horizon.

An access occurs at `90*i/n`, and visits rotate across applications. Raising
the application count does not multiply total demand by that count.
Authorization TTL is a separate 30-day parameter. It can expire while the
underlying credential remains valid. These timings and workloads are modeling
assumptions, not compliance recommendations or observed user distributions.
The configured 10-level credential tree and four issuer slots support the
1,000-credential population case; measurement and extrapolation limits still
apply.

## Common registry trace

Refresh happens at the first access at or after credential expiry. Its new
expiry is that access time plus the validity interval. There is no automatic
paid refresh after the final access. A hidden credential's expiry is bound
inside its leaf, so refresh requires updating the published issuer root as
well as off-chain issuance work.

The population is a **synchronized synthetic cohort**: all members follow the
same relative renewal schedule, while app visits may be rotated. At each
renewal timestamp the common mixed registry receives one unbatched root
publication per person. These publications are counted once globally and
then allocated across the population. They are not charged N times to each
person. This intentionally explicit assumption is not an empirical population
model; unsynchronized arrival times and batching are later alternatives.

Weekly/daily background updates are exogenous and independent of N. In the
population-driven case, N eligibility-preserving background changes are
evenly distributed at `90*(i+0.5)/N`. They affect other leaves without removing
the representative user's eligibility. All updates at a timestamp occur
before access at that timestamp. The model does not invent failures, policy
changes requiring new attestations, or a revoked user's continued access.

Each app's cache is valid only if its epoch is current and its authorization
deadline has not passed. Cache reauthorization bundles the next deposit;
there is no additional standalone deposit charge. A root change invalidates
all cached authorizations even when the particular user's credential is
unchanged. Thus a larger population can reduce fixed cost per person but
increase reauthorization work in the population-driven update scenario.

## Costs and missing prices

The measured first access is a first **holder** access at a service whose
token balance is already nonzero. First access is counted once per visited
app, with the relevant measured repeat/hit/reauthorization event thereafter.
Approval is also counted once per visited app, using the measured allowance
policy. Each complete receipt already includes internal checks and transfer;
verifier gas must not be added again.

The output decomposes:

1. user action gas, including approvals;
2. common registry, hasher, and mock-token deployment plus actual initial-root
   transactions counted once;
3. verifier deployment for ZK variants only;
4. per-app gate deployment and fixture token-balance bootstrapping;
5. shared root-update gas, divided by population for per-user accounting.

Fixed setup represents the **full demonstrator**, including its mock token
and bootstrap transactions. Those fixture components are shown separately;
they are not asserted to be necessary deployment costs of every real service.

Issuer initial/refresh prices, proving-service prices and other operating
costs are unknown. Issuer invoices may already include root-publication gas,
and may be internal transfers under the selected system boundary. Establish
that boundary before adding a quote to known chain fees. The exporter does
not silently combine overlapping charges or present a full monetary total.
Prover milliseconds are resource measurements, not an assumed cash tariff.
Warm successful proofs are pooled with sample-count weights for both ZK
architectures; caching changes proof count, not an invented per-proof speed.
Cold/first timings remain visible in the event summaries.

The price table applies 0.05, 0.4, 1, and 10 gwei as **assumed effective
execution-price levels**, not market quotes. It is unit conversion after the
architecture experiment, not another independent experimental factor.
For OP, the reported ETH amount covers **execution only**: L1 data and
operator fees remain unknown. It must never be labelled a full L2 fee.
No profit, demand, adoption, or optimal user-share claim is computed.

When `fee_snapshot.json` is present beside the measurements (or passed with
`--fee-snapshot`), a separate observed-fee table uses the archived network
summary. Its p10/p50/p90 are **block-weighted percentiles of each block's own
effective p50 execution price**. They are not global transaction quantiles.
Each projection records the exact UTC window, RPC source, summary hash and
raw-archive hash. Ethereum and OP windows have different lengths and are not
time-matched. Local measured gas multiplied by this historical proxy remains
a projection, not a measured mainnet transaction outcome. OP data and operator
fees remain excluded; no other-network fee is substituted when data are absent.

The five user shares (0%, 25%, 50%, 75%, 100%) are retained as five accounting
rules, outside the workload grid. Applied to a selected known execution budget,
user cash is `alpha * budget` and sponsor cash is `(1-alpha) * budget`. Their
sum is unchanged. These are proposed transfers/reimbursements, not gas savings;
they do not change the actual transaction sender without a subsidy mechanism.
Unknown issuer/prover prices and unmeasured OP fee components are outside this
partial budget. No behavioral or willingness-to-pay response is inferred.

## Break-even calculation

For the same workload, let H be direct-path gas minus cached-path gas assuming
no reauthorization after the first access to each app, including the cache
setup premium divided by N. Let q be measured reauthorization gas minus
measured cache-hit gas. The actual cache advantage is:

`saving = H - actual_reauthorizations * q`.

When `q > 0`, caching saves gas exactly when
`actual_reauthorizations < H/q`. The output reports the strict integer limit,
the actual trace count, and whether the inequality holds. Common registry
costs cancel in this within-family comparison because the epoch schedule is
matched. Unknown differential off-chain charges do not become zero: this is
a gas break-even calculation, not a complete monetary break-even claim.

## Output tables

- `event_measurements.csv`: mean/min/median/IQR/max and actual sample count;
  single first observations are identified as such.
- `trace_counts.csv`: 96 contexts, issuance/refresh and global update counts,
  first/repeat/hit/reauthorization counts.
- `trace_events.csv`: action-level state transitions, exact rational event
  times, prior cache epoch/deadline and invalidation reasons.
- `architecture_results.csv`: each context under each architecture and
  available local chain; components and unknown-price expressions.
- `break_even.csv`: matched signed and ZK direct/cache comparisons.
- `price_sensitivity.csv`: explicitly assumed execution-price conversions.
- `observed_fee_projection.csv`: when the archived fee summary is available,
  separate conversions at the network's observed block-fee proxies.
- `allocation_rules.csv`: five conserved user/sponsor allocation rules, not
  an expanded experimental grid.
- `price_inputs.csv`: blank, explicitly unknown external prices.

Every derived table preserves source, measurement-file and exporter hashes.
The traces and population budgets are projections from measured events, not
executed multi-user population benchmarks or measured mainnet outcomes.
