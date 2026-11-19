# Issuer observability pilot

Version 0.2, 16 November 2026. Prepared for Oleksandr Kuznetsov, research review and the economic follow-up. This is a numerical pilot, not a new cryptographic protocol or a submission-ready paper. No new EVM runs were performed.

## Research question

For a linkable holder with one fixed issuer, how much issuer information is revealed by a history of refresh decisions and status-based admission outcomes? What do simple mitigations cost in modeled authorizations and service availability?

The empirical gate passed for this restricted question. The literature/novelty gate remains NOT ESTABLISHED. Universal claims that issuer hiding necessarily requires common invalidation or common failure are not supported.

## Evidence levels

1. Archived measurement replay: 54 scenarios, 8,832 ordinary accesses, from the pinned ECON08 repository snapshot. Every modeled authorization decision matches the archived decision. These are deterministic test fixtures, not field observations or independent samples from a deployment.
2. Counterfactual timing experiment: 12 distinct public update/access schedules deduplicated from those scenarios. Each is instantiated with each of four possible issuers. Selective private invalidation, dummy, cover and every-access variants are models, not measured deployed mechanisms.
3. Synthetic sensitivity: independent Poisson updates per issuer, uniformly sampled access times, fixed TTL and grace, with paired seeds across policies. Population is not estimated. The parameter nu is the expected number of foreign-credential revocation publications per issuer over 90 days; it can be related to r*N/n under an independently specified per-credential process.
4. Synthetic outage experiment: daily source-dated heartbeats and independent two-state issuer outages. Freshness and failure/recovery rates are scenario assumptions, not measured operating reliability.

## Provenance and public projection

Source repository: KuznetsovKarazin/zksnark-benchmark, commit ca1fabbb1d2fb777adca87544e689a14f6b5fbdb. inputs/source_index.json records exact paths and Git blob hashes. Archived report/access files are also checked against their original SHA-256 manifests. Raw receipts/proofs are not included or reverified here; this is not a new cryptographic verification campaign.

results/public_observations.json retains only target handle, public policy/group, source publication times/issuer labels, and access times/full-versus-cached classes. results/evaluation_truth.json keeps true issuer labels separately. The inference API rejects observation fields other than at and refresh. Fixture ordering, holder_issuer, witness/proof inputs, and the fact that the cohort has one holder per issuer are not attacker inputs.

The archived full/cached labels are harness annotations of distinct public depositZK/depositCached calls, documented in inputs/archive/harness.mjs. This pilot uses their public-method interpretation; it does not independently decode every archived transaction. Publication issuer labels are public in this harness (issuer index and sender). An independently engineered transaction decoder is still required before describing the result as a deployed-chain attack.

Actual B2 and B4 registries disclose their group; B4 already has one candidate by policy. The counterfactual selective cache preserves a hypothetical shared public interface and starts with four candidates. It must NOT be described as discovering hidden issuers in the existing B4 implementation.

## Timing observer and state

The observer links every ordinary access of one holder, sees full authorization versus cache hit without error, knows the TTL, grace delta, and issuer-labeled publication times. It has no signing key, credential, witness, proof secret, or issuer metadata from the fixture. Target credentials are never revoked; updates concern other credentials. All requested accesses succeed. Access schedules are exogenous and independent of issuer. There is one fixed issuer throughout the observation window.

The initial named-issuer prior is uniform over n=4. Nonuniform priors are supported and checked but the main grid uses uniform priors. Entropy is in bits, maximum 2; support is the count of positive-posterior candidates. A singleton is exact identification under the stated model. A 0.95 maximum posterior is a confidence threshold, not a cryptographic guarantee.

Let a be the time of the last publicly observed full authorization. An authorization is forced for issuer i at access t if this is the first access, t >= a+TTL, or a publication of that issuer occurred at u>a and its first such publication has u+delta <= t. Publications at the same time as a full authorization are already absorbed by that authorization. The earliest invalidation deadline is not postponed by later updates. Delta is an acceptance grace, not a batching interval.

Policies:

* common: any issuer publication invalidates the cache under the same rule.
* selective: only the target issuer publication invalidates. This is an IDEALIZED private-invalidation oracle; a sound and private contract/circuit implementing it is not supplied.
* dummy_rho: selective invalidation plus a full authorization with probability rho at every otherwise cached access.
* cover_rho: selective invalidation plus a full authorization with probability rho only when the common policy would require it. A fresh independent decision is made on each such access until a full authorization resets the common condition. This is event-triggered cover, not one coin per publication.
* one_coin_rho: one independent coin for each foreign publication, selected once with probability rho; an own publication is always selected. A selected outstanding event forces a full at its deadline; a skipped event is never retried. Any full absorbs all prior events.
* every: a full fresh proof on every access.

All dummy/cover full authorizations are assumed indistinguishable from required authorizations on the modeled interface. This is optimistic: calldata, events, gas, addresses and proof structure may distinguish a practical implementation. No differential-privacy claim is made.

Let f_i(t,a) be the forced-refresh predicate and q_i the policy's refresh probability. For dummy, q_i=1 when f_i=1 and q_i=rho otherwise. For cover, q_i=0 when neither own nor common invalidation applies; otherwise use the preceding probabilities. Given observed y in {refresh,hit}, update p_i proportionally to p_i*q_i for refresh or p_i*(1-q_i) for hit. On any observed refresh, a=t for every candidate hypothesis. Thus a is observable and the sequential filter is exact without hidden-cache state integration. Zero-likelihood candidates are eliminated exactly.

The filter is checked against a separate full-history likelihood evaluator on all possible five-observation binary transcripts for the test parameter grid. Probabilities sum to one. Additional unit tests exercise source-time equality, TTL/grace boundaries, nonuniform priors and secret-field rejection.

## Negative controls and label knowledge

No publications, common refresh, every-access proof, simultaneous updates of all issuers, and TTL expiry on every request do not reveal issuer through the modeled refresh class. An additional control averages the likelihood over all 24 unknown permutations of four issuer labels. With an exchangeable prior the named-issuer posterior remains uniform, even when a labeled observer identifies the issuer. This is a symmetry control, not a complete model or attack assessment of Ethereum Foundation's anonymous-publication design. Nonexchangeable rates, collusion or external labels can break that symmetry.

An observer that cannot link accesses cannot automatically combine these histories. A holder that changes credential/issuer, an unobserved reset, missed updates, uncertain TTL, or a noisy method classifier requires a different likelihood model. The pilot's exact singleton rates are not deployment success probabilities.

## Gas accounting

All counterfactual timing policies use the SAME archived B1 median coefficients: first=464200, cached=67610, reauthorization=355749 gas. For m accesses and R full authorizations, C=464200+(R-1)*355749+(m-R)*67610. This is a common access-gas proxy, not a measured cost of the proposed selective mechanism or fresh-set circuit. It excludes approval, setup, issuer publications, heartbeats, proof generation, paymaster and any added verification/storage overhead. Absolute euro prices are deliberately not added. Differences in publication count are zero in this timing comparison. Existing B1 common reauthorization counts are replayed, but using medians does not exactly reproduce its receipt-by-receipt gas total.

## Freshness and availability observer

Daily heartbeat publication while online provides honest, complete source-dated status. At noon on day d, issuer j is fresh if d+0.5 < s_j+F, where s_j is its last successful publication day. Publication delay is zero. Outages pause publication; they do not revoke the target credential. F is a fixed source-age cap. Public S(t) lists fresh issuers. No security improvement over standard freshness requirements is claimed.

The strong observer knows a holder attempts every scheduled access and observes both accept and deny. This covers visible on-chain attempts/reverts or a verifier with complete request logs, not an outsider who sees no client-aborted requests. A separate positive-only statistic intersects S(t) only at successful presentations. It is a logical exclusion metric, not a calibrated posterior using absence. Exact identification by positive evidence alone survives removal of denial observations.

Common admission serves all holders only when every issuer is fresh. Fresh-k serves issuer i when i is in S and |S|>=k. The latter checks only the current set and can violate a history-wide anonymity goal. Under one fixed issuer, successful presentations imply C_t subset of the intersection of all successful S(t). In addition, with visible attempts a rejection when the current set is large enough implies membership in the excluded branch. These are policy disclosures, not a break of zero knowledge.

## Two-sided history guard

For a public history with candidate set C, a deterministic admission policy chooses accepting set A subset of C intersect S. If all attempt outcomes are observable and the required support is k, every nonempty outcome branch must contain at least k candidates. Necessary and sufficient one-step conditions are A empty, A=C, or both |A|>=k and |C minus A|>=k.

The pilot guard chooses A=C if C subset S. Otherwise, if |C|<2k or |C intersect S|<k, it chooses A empty. In all other cases it selects min(|C intersect S|, |C|-k) fresh issuers by a fixed public ordering. After success C becomes A; after denial C becomes C minus A. Induction gives support at least k for every feasible transcript starting with |C|>=k. The implementation is checked exhaustively over 15,472 (n,k,C,S) combinations for n=2..6 against all possible accepting subsets, and over all three-step mask histories for n=4,k=2 in unit tests.

This guard maximizes the NUMBER of accepted candidate issuers at one step under the cardinality constraint. It does not optimize expected welfare with unequal priors, multi-step availability, fairness, or gas. Its ordering can discriminate among issuers; no strategyproofness is claimed. It is an admission oracle, not a deployed circuit.

For |C|<2k, no nontrivial deterministic split is possible. In particular n=4,k=3 forces common failure whenever any candidate is stale, if all attempts/outcomes are visible. This conditional elementary partition result explains coupling within this model; it is NOT an impossibility theorem for issuer-hiding credentials generally. Randomized policies, hidden attempts, unlinkable sessions, different guarantees and alternative revocation authorities are outside it. Cardinality k is not an entropy guarantee under unequal priors.

## Interpretation and decision

The pilot establishes a working experiment and reproduces a real distinction between common-cache behavior and an ideal selective schedule. It also rules out the proposed instantaneous fresh-set threshold as a history-wide protection. It does not establish scientific novelty: selective-revocation attacks, timing correlation, anonymity-set intersections and partitions have extensive antecedents.

The v0.2 conditional lower bound and matched coalition quantities support a bounded economic follow-up on cost incidence and compensation. A new cache implementation is not required for the stated architectural bound. A broad EVM campaign and a publication novelty claim remain unjustified until independent review assesses the distinction from prior work. If the results are routine consequences of known attacks, preserve the protocol checks and evaluate the economic article on its own merits.


## Version 0.2 additions

The formal cache-architecture propositions and their proofs are in
[CONDITIONAL_RESULTS](proofs/CONDITIONAL_RESULTS.md). Common invalidation minimizes
the number of full authorizations, and therefore fixed-coefficient access gas,
under the stated mandatory-refresh and service constraints. It is not a universal
claim about every issuer-hiding construction, monetary cost under varying prices,
or a new deployed protocol. Independent novelty review remains open.

### Exact inference for one coin per publication

After an observed full, all earlier publication coins are irrelevant. After a hit,
all expired foreign coins since that full are known to have been zero under each
surviving issuer hypothesis. At the next access, let k_i be the number of newly
expired foreign publications, excluding those already tested by a hit or absorbed
by a full. If own invalidation or TTL requires refresh, its probability is one;
otherwise the hit probability is (1-rho)^k_i. Bayes uses this probability directly,
without resampling failed coins. A separate oracle explicitly enumerates all
hidden coin assignments on small schedules. Tiny hit likelihoods are kept separate
from 1-minus-hit to avoid rounding a positive value to zero.

The worst-case two-sided epsilon is infinite for any informative own-versus-foreign
event with rho<1. Mean entropy, Bayes identification accuracy and singleton
probability are distinct descriptive metrics. No finite pure-epsilon privacy
frontier is claimed. In weekly W08, with three own and nine foreign events,
E[R]=4+9rho; final support has distribution 1+Binomial(3,rho^3). The prior is uniform.
Exact formulas are independently checked against all 4096 event-response strings
for each of 21 rho values. The full grid also includes overlapping publications,
TTL effects and delta=0,1,3,7,14 days, where the weekly formulas need not apply.

### Anonymous cohort experiment

A public holder handle links accesses but carries no issuer label. Each experiment
has four issuers and 4, 8 or 16 holders per issuer. Handle order is shuffled
independently of true issuer. All holders have independently sampled request times
with the same activity distribution; coin streams are separate per holder.
Public input to the attacker contains only anonymous publication timestamps and
full/hit observations. Both publication issuer fields and holder truth fields are
rejected by the feature API. Ground truth is used only by the generator/evaluator.

For each holder and publication, use the first access at which exactly that one
new publication deadline became eligible since the preceding access, provided the
publication was not already absorbed and the TTL is still valid. Record full=1 or
hit=0; overlapping, unobserved or TTL-confounded opportunities are missing. Pairwise
distance is the mismatch fraction among shared features; fewer than two shared
features gives uninformative distance 0.5. Average-linkage agglomeration produces
four groups, using the publicly known issuer count. There is no label training or
test-label hyperparameter selection. The attack is a fixed baseline, not an optimal
attacker. Inactivity and missing features can substantially weaken it.

Report adjusted Rand index, pairwise same-issuer AUC/precision/recall and the mean
number of shared features. After clustering, reveal only the issuer of handle H000
as one external anchor. Label its cluster and count correct, wrong and unassigned
other holders. Precision is pooled over actual predictions; coverage and wrong
attribution rate have denominator all non-anchor holders. Correct clustering does
not itself name issuers, and one anchor is not guaranteed to identify a pure cluster.
Common-response and no-publication controls have pairwise AUC 0.5; a truth-label
shuffle is reported for every run. This is not an attack demonstration against EF.

### Economic handoff

For holder group i and foreign coalition S, v_i(S) is modeled access gas under
updates from i and S minus modeled access gas under only i. The exact common greedy
policy is used in each coalition, with identical holder request times. This includes
TTL shifts and gives net differences rather than charging every positive difference
while ignoring later credits. All eight foreign coalitions are evaluated for each
of four target groups. The supplied reference computes the Shapley allocation and
a simpler publication-count proportional allocation; both sum to the same net
externality. They are accounting transfers, not gas savings or proof that issuers
will accept a fee. The baseline selective cache is still an oracle.

Three worked cases are supplied: weekly A=4, weekly A=32, and an asymmetric A=32
model with issuer update means [1,3,6,12] over 90 days and independent holder times.
A is active holders, not the issued population N. There is no new A=32 EVM point.
Historical q0/e0 are available for illustrative conversion; downtime remains in
request units unless an independently justified value is provided.

### Beneficiary-funded economic benchmark

Economic handoff revision 2 adds equal allocation of the aggregate access premium
per active holder. It changes the payment comparison, not the observer model or
any technical result. For group g, the final access burden is its selective
baseline plus A_g/A of the total common-minus-selective premium. The payment
table reconciles this with actual common-policy gas through net holder-to-holder
settlement; issuers are not charged. Equal sharing is a normative comparison,
not an estimate of benefit valuations, demand or incentive compatibility.
See handoff/START_HERE.md for scope and the symmetric control.
