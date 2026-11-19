# Conditional optimality of common invalidation

Version 0.2, 16 November 2026. These are statements about the specified cache
architecture, not impossibility theorems for issuer-hiding credentials generally.
The proofs and enumerations have been checked in this package; independent review
and a full novelty assessment remain outstanding.

## Model and cost boundary

Fix an exogenous sequence of successful requested accesses t1 < ... < tm, one
unchanging hidden issuer i in a public group G, a common initial state, a positive
TTL T, a nonnegative grace delta, and issuer-labelled publication times P_i.
Publications at an access timestamp precede that access. A full authorization at
a absorbs every publication at u <= a and starts a new TTL. No other operation
can refresh the credential's cached status. A hit performs no independent current
non-revocation proof or trusted private status update.

The architecture requires a full authorization at t for issuer i if no previous
full exists, t >= a+T, or there is u in P_i with a < u <= t-delta. Target credentials
are unrevoked: publications change other credentials' status. This mandatory
cache-invalidation rule is an explicit assumption, not a consequence of credential
security in every possible architecture. All requested valid accesses must be
served; rejecting, delaying or silently dropping a request is not an allowed way
to save a full authorization in this proposition.

The observer links the accesses, sees their timestamps and full/hit classes, and
knows the public input sequence. Compare issuer hypotheses while holding this
public input fixed. Security has zero error. Costs are fixed constants c_first,
c_full and c_hit with c_full > c_hit. Only this access-cost boundary is minimized.
Setup, publication, proof generation, sponsorship, and prices varying with time
are outside the cost statement.

## Proposition 1  Necessary common invalidation

For a deterministic policy whose complete observable transcript is identical for
every issuer hypothesis in G, a hit at public history h is possible only if it is
valid under every issuer hypothesis. In particular, an outstanding publication
from any member whose grace has expired forces a full authorization at the next
requested access, unless an intervening full has already absorbed it.

Proof. At the same public history, the last full authorization a is observable
and identical under every hypothesis. If issuer j has an outstanding expired
publication, a hit is invalid under hypothesis i=j. Zero-error safety requires a
full. Transcript identity requires the same full under every other hypothesis.
The TTL and initial-authorization cases are common to all hypotheses. Conversely,
the common policy applies precisely the union of these requirements and depends
only on the public input, so its full/hit transcript does not identify i. End.

The statement does not require one transaction per publication: multiple updates
can be absorbed by one full. Nor does it claim immediate proactive activity when
the holder makes no request.

## Proposition 2  Minimum number and fixed-coefficient gas

Let g1,...,gr be the full-authorization times of the common policy that refreshes
only when required. Every admissible identical-transcript policy has at least r
full authorizations, including the initial one. Consequently the common policy
minimizes c_first + (r-1)c_full + (m-r)c_hit in this architecture.

Proof. Proposition 1 makes every admissible transcript feasible for the union of
all publications. A later last full can only weaken the next refresh requirement:
it absorbs a superset of publications and has a later TTL deadline. Let s1,s2,...
be the full times of any feasible alternative, allowing proactive refresh at any
requested access. Both schedules start with g1=s1=t1. Inductively assume sk<=gk.
At g(k+1), if the alternative has already made its (k+1)th full, then s(k+1)<=g(k+1).
Otherwise its last full is sk<=gk; since the common policy is forced to refresh,
monotonicity forces the alternative to refresh by this access as well. Thus every
gk requires the existence of sk, so the alternative has at least r full calls.
The fixed-coefficient cost is increasing in their count. End.

The exchange/monotonicity argument is elementary. Its application and measured
boundary must be distinguished from a claim that this mathematical technique is
new. The exhaustive check covers 576 small schedules and every feasible proactive
full/hit alternative. It is a check, not a substitute for the proof.

A time-varying gas price breaks the monetary-cost corollary: access at 1 can
refresh a publication at 0.5 before its grace deadline 2. If the price at 2 is 100
times the price at 1, early refresh and a later hit can cost less money than the
greedy common schedule, with the same number of authorizations. The numeric
counterexample is in results/extension_checks.json.

## Corollary  Randomization with a finite likelihood-ratio guarantee

Suppose instead that complete transcript distributions satisfy P_i(E) <=
exp(epsilon) P_j(E) for every event E and every ordered pair i,j, with a finite
epsilon, under the same zero-error safety and service assumptions. They must have
the same support. Any positive-probability public prefix is therefore feasible
under every issuer. If a hit extension has probability zero under one issuer
because refresh is mandatory, it has probability zero under all issuers. Every
realized transcript is feasible for the common union, and Proposition 2's count
bound still holds. Perfect distributional hiding is epsilon=0 as a special case.

This is a transcript-indistinguishability definition, not a claim that an arbitrary
database adjacency relation has been supplied. The support argument is standard;
see Dwork and Roth, Definition 2.4, for the all-events likelihood-ratio requirement.

For one isolated update the one-coin policy has P(full|own)=1 and P(full|foreign)=rho,
but P(hit|own)=0 and P(hit|foreign)=1-rho. Hence ln(1/rho) describes only the full
outcome. The worst-case two-sided privacy loss is infinite whenever rho<1. For an
additive-slack variant P_i(E)<=exp(epsilon)P_j(E)+eta, this isolated binary channel
requires eta>=1-rho, and eta=1-rho suffices for all epsilon>=0. This is a one-event
statement, not a full-history composition claim. Delta continues to mean timing
grace; eta avoids reusing that symbol for privacy slack.

## Proposition 3  Availability under perfect hiding

Fix a known candidate set C, a public fresh-issuer set S and an observable attempt
whose outcome is accept/deny. Suppose acceptance is safe only for i in S and
perfect outcome hiding is required over every i in C. If C is not a subset of S,
some hypothesis must have acceptance probability zero, so all hypotheses must.
When C is a subset of S, accepting all candidates maximizes service availability.
Common admission is therefore pointwise availability-optimal under these strong
observation and privacy assumptions. The same zero-support argument applies to
a finite two-sided likelihood-ratio guarantee. Unobserved client-aborted attempts,
unlinkable presentations and different safety guarantees require another model.

For cardinality k rather than perfect hiding, a deterministic accepting subset
A of C intersect S is safe for history-wide support only when A is empty, A=C,
or both |A|>=k and |C minus A|>=k. This is a supporting partition lemma. It is not
claimed as original. The supplied guard maximizes one-step accepted cardinality,
not multi-step welfare, fairness or entropy under unequal priors.

## Attribution and limits

Intersection/disclosure attacks precede this work; see Danezis 2003 and Danezis
and Serjantov 2004. These references establish the attack family, not an assertion
that the above lemma is quoted from a particular theorem there. ABC4Trust already
discusses selective revocation and update timing. Our possible contribution is a
precisely scoped boundary plus quantitative access costs and externalities, not
the invention of temporal inference, intersections or likelihood-ratio privacy.

EF uses a shared revocation registry with anonymous writes and off-chain proofs.
Nothing here demonstrates a visible full/hit cache channel in that implementation.
The anonymous cohort experiment is a separate hypothetical cached application.

Sources and links: [related work](../review/RELATED_WORK.md).
