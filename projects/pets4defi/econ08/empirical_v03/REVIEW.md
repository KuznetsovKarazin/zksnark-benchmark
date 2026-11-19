# Technical review of the proposed empirical extension

17 November 2026. This review distinguishes real observations, executed
implementations, synthetic stress tests and remaining publication gates.

## Overall judgment

The direction is sound, but the five work packages have different evidentiary
roles. The strongest paper is not simply a larger benchmark: it explains when
an issuer-dependent cache response defeats issuer hiding, measures what an
observer can extract, and demonstrates the cost and freshness consequences of
an implementable alternative.

The phrase "everything is synthetic" is too broad. The earlier contract and
Groth16/EVM executions are actual implementations; workloads and the idealized
selective invalidation oracle are the external-validity weaknesses. A public
testnet makes the extraction path independently observable. It does not make
the synthetic access schedule or hypothetical issuer assignment empirical.

## 1. Real schedules: valuable, but the proposed data gate did not pass

The frozen window is 2026-08-19 00:00 UTC through 2026-11-17 00:00 UTC (exclusive).
On-chain-only EAS indexer pagination completed and the returned counts matched
separate aggregate queries:

| Chain | Revocations | Attester addresses | Attesters meeting the full gate |
|---|---:|---:|---:|
| Ethereum | 5 | 4 | 0 |
| Base | 23,125 | 18 | 2 |
| Optimism | 6 | 1 | 0 |

The full gate is at least 1,000 attestations issued before the window end and
revocations on at least ten distinct UTC days. The planned experiment requires
four qualifying attesters. Only three Base attesters reach ten days; one of
those has only 17 attestations. The two qualified sources have:

| Local source | Revocations | Active revocation days | Attestations before window end |
|---|---:|---:|---:|
| Base source 1 | 22,969 | 90 | 1,232,657 |
| Base source 2 | 95 | 18 | 3,448 |

Source 1 contributes 99.33% of Base revocations. This is an event-frequency
share, not an estimate of the issuer prior for an arbitrary DeFi holder.
Several schemas from one attester must not be counted as independent issuers.

These are indexer observations, not a complete independent chain-log audit.
Historical RPC coverage encountered HTTP 403 responses in this execution
environment. A separate GitHub runner reproduced the exact Ethereum and Base
revocation-file hashes and Base aggregate count, but encountered an Optimism
HTTP 502 and a timeout on one issuance-count query. Consequently the separate
CI data screen remained UNKNOWN. Its successful workflow status means the
checks executed, not that the empirical gate passed.

The proper response is to retain the failed screen, seek additional genuinely
independent sources/windows if needed, and clearly label any calibrated
synthetic fallback. Do not lower the gate silently or duplicate two empirical
sources into four purported real issuers.

`calibrated.py` implements an explicitly exploratory fallback: the two observed
daily profiles are duplicated across synthetic issuers with random circular
shifts and equal template weights. Accesses remain synthetic. This preserves
some measured schedule properties but does not establish real-world attack
accuracy. Daily coalescing also loses within-day bursts. Credential-revocation
events must not be confused with measured root-publication transactions.

The completed fallback comprises 60 runs (4/16/64 synthetic issuers, 20 seeds,
1,000 holders). Mean final identification accuracies are 73.77%, 53.98% and
42.00%, respectively, at 10% label error and 10% missed accesses. For comparison,
the separate 1,000-holder nominal-rate study gives 99.36%, 97.24% and 93.03%.
This is a sensitivity comparison, not an estimate of empirical accuracy. In
particular, duplicating a source active on every day creates exchangeable
synthetic issuers. The control illustrates why distinct real sources and a
realistic update regime matter; it must not be advertised as finding dozens of
independent real issuers.

The Aave/Compound acquisition and normalization code is provided, but no
complete 90-day real-access dataset is claimed. Supply beneficiaries, withdrawal
owners, contract wallets and routers are not interchangeable with transaction
senders or persons. Excluding addresses with fewer than three accesses requires
reporting the excluded counts. Whole-path resampling is preferable to drawing
independent gaps when studying sessions and calendar correlations.

## 2. Public testnet: an engineering gate, not economic ground truth

The extractor uses only transaction calldata, receipts/events, block headers and
explicit deployment allowlists. It validates status, block/transaction linkage,
calldata/event agreement and unknown method classes. A successful failed-call
classification is not a successful authorization. Archive validation covers
15,346 transactions and 8,875 successful accesses with zero mismatches across
25 archived local-EVM runs.

The live-capable harness deploys the batched registry, unchanged gate, verifier
and test token, creates 32 or 128 synthetic wallets, and produces real proofs.
The saved local runs do not close the public-testnet gate. The preflight found
no configured funded signer, and the testnet endpoint timed out. No public
deployment address or transaction hash is invented.

Testnet gas measurements are useful. TestETH charges are not observed euro
costs or mainnet L2 prices. OP-chain fees may include execution, L1 data and
fork-dependent operator charges; unknown components must remain unknown.

## 3. Batched combined root: implementable with explicit trust and freshness

The existing registry exposes the changed issuer in calldata/events and public
leaf-root storage; it also rejects unchanged roots. Simply bundling its calls
or adding a common event does not achieve publisher hiding.

`BatchedPolicyRegistry` instead accepts a combined root from a trusted
coordinator. It does not change the four-issuer circuit or PolicyGate. All
holders share cache-epoch invalidation; even an unchanged-root heartbeat
advances that epoch. Missed updates eventually stop authorization. Local checks
exercise real proofs, invalidated caches, stale and queued proofs, unauthorized
publication, same-root heartbeats and the strict acceptance deadline.

The root's correctness, completeness of issuer inputs and private witness
delivery remain operator assumptions. A public source like EAS still exposes
its attester; batching cannot make that source private. The relevant protection
is removing the issuer-specific holder response in the modeled channel.
Auxiliary links, witness delivery, unsuccessful eligibility and revocation of
the holder's own credential remain separate channels.

The coordinator assumption is substantive: an unrestricted root publisher can
commit unauthorized credentials, not merely delay updates. The current adapter
is therefore not a trust-preserving replacement for independently authenticated
issuer-root submissions. Joint approval of the combined root is one possible
alternative, with its own signing and availability costs. The present prototype
tests the explicitly trusted-operator variant.

The claimed benefit concerns incremental leakage from cache responses,
conditional on access behavior. It does not remove issuer information already
present in issuer-dependent access patterns. The current stress model makes
accesses independent of issuer; the counterfactual replay randomizes that
assignment. This is an experimental control, not an observed population fact.

P + L <= F is valid only when L covers ingestion, publication and the applicable
finality bound and no extra cache/root grace is accepted. The contract enforces
deadlines but cannot enforce upstream correctness or availability. Required
mode is ZK, policyMode 1, zero delta and zero root grace. Mode 0 does not call the
freshness hook and is unsupported by this adapter. The prototype is not a
production security audit.

Grouping reveals the group. Its entropy depends on priors, and matched-rate
groups need comparison against random groups. These implementation choices
have not been shown optimal. Counts of full authorizations depend on accesses
occupying periods and TTL; 90/P is not a general cost formula.

## 4–5. Scale and stronger attacks: useful if the model remains explicit

The HMM marginalizes hidden issuer, cache age and pending invalidation. It
handles missed full authorizations as hidden state resets. Independent scalar
enumeration confirms its likelihood on small examples; noiseless cases match
the original v0.2 filter. Common-channel and random-label controls preserve
even a nonuniform prior. Consistent permutation is checked as invariance.

The initial matrix contains 1,600 completed runs: 80 cases, 20 seeds, 128
holders per run. For selective invalidation, 20% label error and 30% missing
accesses still give 89.92% final accuracy for four issuers (uniform-prior
baseline 25%) and 54.84% for 64 issuers (baseline 1.5625%). Seed-level 95%
interval half-widths are 1.23 and 2.57 percentage points respectively.

Those rates assume known observation parameters, issuer-independent daily
Bernoulli access with probability 0.45, and the specified heterogeneous
synthetic publication process. They are robustness results, not measured error
rates of a real classifier and not empirical identification of deployed users.
First confident wrong identifications are also recorded; accuracy and posterior
confidence are different metrics. Seeds quantify simulation uncertainty, not
independent replication over real time windows.

Sparse spectral clustering avoids storing a full holder-by-holder similarity
matrix. The 10,000-holder cases are scalability demonstrations, one seed each.
Clustering is evaluated without label names via ARI/AMI, with a separate
independent-truth-permutation control. A disclosed-anchor experiment excludes
anchors from accuracy and reports abstention coverage. Failure of a clustering
algorithm is never treated as proof of privacy.

## Publication decision

JISA is thematically appropriate for an applied privacy/access-control study.
The official scope emphasizes practical implementation, empirical testing or
industrial relevance; it does not impose a universal requirement to find a
deployed victim system. A public prototype, independently reproducible attack
path and careful limits can provide practical evidence even if the real-data
gate fails. Acceptance remains a scientific judgment, not a guarantee.

Before a submission claiming the empirical headline: obtain sufficient real
sources and verified access coverage, or rewrite the claim as calibrated
systems analysis; finish a public testnet extraction run; and evaluate the
freshness/availability cost of the defense under the final threat model.
Large synthetic grids alone do not solve external validity. The contribution
should be the measured observability–cost–freshness trade-off, not a claim of a
new cryptographic primitive or an unprecedented generic revocation side channel.

Primary scope source: https://shop.elsevier.com/journals/journal-of-information-security-and-applications/2214-2126
Protocol/source links and reproduction commands are in README.md. Exact
completed-run status is in STATUS.md.
