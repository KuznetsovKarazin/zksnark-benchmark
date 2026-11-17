# Model scope and conditional guarantees

## What the common-cadence control establishes

Let Z be the hidden issuer, A the complete holder access path, C the common
publication cadence, and Y the observed full/hit transcript. Suppose:

- all candidate issuers are in the same public group;
- every credential remains eligible throughout the analyzed interval;
- TTL and the relevant expiry behavior are issuer-independent;
- refresh decisions depend only on A, C and that common TTL;
- observation errors and missed calls are independent of Z conditional on the
  public experiment inputs.

Then the modeled observation channel satisfies
`P(Y | Z, A, C) = P(Y | A, C)`. Bayes' rule therefore gives
`P(Z | Y, A, C) = P(Z | A, C)`: the cache-response channel adds no issuer
information under those assumptions. This is a conditional channel property,
not a new cryptographic theorem or a claim of system-wide unlinkability.

It does not hide a public group, remove a nonuniform prior, erase an attester
named by EAS, conceal issuer-correlated activity, or cover witness distribution,
network identity, gas/call-data side channels beyond the classified method,
credential expiry differences, denials or revocation of the holder's own
credential. The HMM's common-cadence tests check this conditional property.

## Why freshness and availability must be accounted for together

For a slot cutoff c and period P, a revocation arriving just after c can remain
unreflected until the next cutoff plus bounded ingestion/publication/finality
lag L. Accepting the old state beyond c + P + L violates that claimed bound.
The adapter therefore caps acceptance at that deadline and accepts no extra
cache or old-root grace. If an update is missing, access fails closed.

Thus P + L <= F is a sufficient schedule constraint only when the root inputs
are correct and complete and L is actually bounded as assumed. The contract
cannot establish those off-chain premises. Common acceptance deadlines protect
freshness by sacrificing availability during missed publication slots.

## Statistical interpretation

The main and one-factor-at-a-time studies independently generate schedules and
holder assignments for each seed. Intervals use seed means, not correlated
holder-day observations. The calibrated fallback conditions on two fixed
indexer profiles and randomizes synthetic template shifts/assignments. It
measures Monte Carlo variation, not uncertainty over all real issuers or time.

Final top-label accuracy, first threshold crossing of the true issuer, and the
first confidently wrong prediction are different statistics. Never-identified
holders remain censored. A median computed only over identified holders is
explicitly conditional and is not a population median identification time.

The one-seed 10,000-holder clustering cases establish that the implementation
ran at that size. Their ARI/AMI and anchor accuracies have no across-seed
confidence interval. A consistent relabeling is an invariance check; the null
control independently permutes evaluation truth relative to observations.
