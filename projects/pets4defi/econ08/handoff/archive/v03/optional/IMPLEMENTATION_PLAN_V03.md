# Research plan for private eligibility funding

ECON-07 + ECON-08, version 0.3, 13 November 2026.

**For information only for Nataliya.** Her required first reading and return are defined in `handoff/START_HERE.md`. Oleksandr owns the technical gates in this plan. Version 0.3 supersedes the v0.2 assignment; accepted ECON-07 calculations and archived measurements retain their original scope and attribution.

## 1. Research question and candidate contributions

**What resource cost, holder funding, sponsor support and payment-time liquidity are required to operate private eligibility under a specified privacy and revocation requirement, and when do explicit funding restrictions change the preferred configuration?**

The design is `x=(B,δ,TTL)`. The resource objective remains minimum lifecycle cost, but the study reports the funding requirements as outputs. It does not assume that financial constraints must reverse a technical optimum. A change of optimum is one possible finding, not the sole definition of success.

The research programme has four connected questions. They expand the potential contribution without committing to a large EVM campaign.

| Question | Required result | Why it might add to PUB-01 |
|---|---|---|
| RQ1. When can financing change design choice? | State the no-reversal baseline; identify which payment routes, earmarking or payment times break it; quantify any resulting choice or exclusion region. | Distinguishes resource optimization from implementable financing rather than relabelling a subsidy fraction. The elementary baseline lemma alone is not a new scientific contribution. |
| RQ2. What funding is required? | Compute holder-budget versus sponsor-support frontiers and actor-specific minimum initial liquidity. Report derivatives or finite differences for stricter privacy/freshness where meaningful. | Makes budgets outputs and shows the cost incidence and liquidity price of each requirement, rather than choosing arbitrary willingness-to-pay caps. |
| RQ3. Which operating regimes matter? | Locate conditional active-population and grace/TTL boundaries, including regimes where more grace changes no authorization count. Test the robustness of those boundaries to activity and price uncertainty. | Must go beyond PUB-01's grouping, Poisson, TTL and activity examples by answering the funding/frontier question with validated event semantics. |
| RQ4. How much protection against variation is needed? | Compare mean funding with a stated reliability or stress requirement for holder payment, sponsor outlay and cash shortfall under simulated workloads. | A conditional reserve/reliability result may remain useful even when expected resource rankings never reverse. It needs a defined stochastic process and validation, not merely a renamed mean-cost plot. |

The paper need not claim all four as separate contributions. G0a selects the smallest coherent supported set. If the remaining results are simple rescalings of PUB-01 or of accepted ECON-07, stop the expanded campaign and revise the question. A negative design-reversal result is useful for framing but does not by itself establish sufficient journal novelty.

## 2. Novelty boundary and accounting baseline

PUB-01 already includes finite-horizon authorization recurrence (§3.5/Figure 3), population-dependent revocation rates (§5), issuer partitioning and setup/holder trade-offs (§4.4), TTL/activity examples and cost sharing (§3.6/§4.6). Recheck locators against the submitted version. Cite it as predecessor, distinguish new evidence and reuse no submitted figure.

The new work must connect the event model to an explicit financing architecture and the resulting budget/liquidity frontier. Simply repeating E[R] against update intensity, sweeping gas prices or discovering a known setup amortization crossover is not sufficient. The accepted ECON-07 ledger and payment rules are prior work within this project, not unperformed tasks.

Let `C_x` be total real resource cost for a technically admissible design. With the same available total finance `F`, arbitrary costless transfers, and no restrictions on payment timing, route or use, feasibility is equivalent to `C_x≤F`. Consequently, if any design is feasible, a minimum-cost design is feasible. Multiplying gas by a different positive price cannot invalidate this implication.

For `A` identical active holders with a uniform budget limit `b` and freely allocated sponsor support up to `s`, the baseline funding frontier is

`b_min(x;s) = max(0, (C_x-s)/A)`.

This is conditional on the sponsor bound and allocation rules. An unlimited sponsor makes a zero holder budget unsurprising. Do not report a unique “minimum budget” without specifying who else may pay and when. Internal transfers cancel from total resource cost. Reserve principal is a stock; financing cost, expected loss and settlement expenses require separate definitions.

Restrictions are scenarios unless supported by an implementation, contractual rule or other evidence. Examples to test independently include: holders cannot prepay shared deployment; sponsor funds can cover only shared operator costs; reimbursements arrive after users must fund transactions; paymaster sponsorship covers only defined operations. Do not choose restrictions after seeing a preferred reversal. ERC-4337 requires adequate deposits before sponsored operations; public sponsorship-policy documentation also illustrates per-operation, per-user and aggregate limits. These sources motivate a class of constraints, not measured prices, implemented paymasters or the actual rules of this project. Any added paymaster overhead is outside current measurements. A shared-cost-only sponsor with no holder-to-operator transfer has feasibility `s≥S_x` and `b≥h_x`, where `S_x` is shared cost and `h_x` per-holder cost; it is an illustrative architecture, not observed project policy.

## 3. Evidence and current numerical anchors

The preserved archive contains 32 pilot and 22 cohort scenarios, 8,832 ordinary accesses, 512 proofs including timing observations, and 10,627 signed transactions including setup, publications and diagnostics. Cohort N=16/128/512 means issued credentials, with only four measured active wallets. These are not population-scaling experiments. The fixed weekly schedule has twelve publications irrespective of N.

In N=16/A=4/HIGH/weekly/δ=0, authorization totals for B=1/2/4/signed are 52/28/16/12; no-update totals are 12 for each. Distinguish initial, TTL-triggered, revocation-triggered and excess-versus-control authorizations. Renewal-time shifts make these counters different quantities.

The historical price anchor is q0=0.130658648 gwei/gas and e0=2164.73 EUR/ETH, not a current quote. The four-wallet B1-minus-signed difference is 10,176,740 gas, or EUR 0.719599 per active wallet over 90 days. “Privacy is cheap” or “KYC dominates” remains conditional on workload, boundary and prices.

Under linear replication of the fixed observed holder workload:

| Design | Shared gas S | Per-holder gas h | Projected total G(A)=S+A h |
|---|---:|---:|---|
| B1 | 13,817,033 | 10,653,405 | 13,817,033 + 10,653,405 A |
| B2 | 16,592,944 | 8,930,165 | 16,592,944 + 8,930,165 A |
| B4 | 24,791,056 | 8,068,512 | 24,791,056 + 8,068,512 A |

B4/B2 cross at A≈9.5144, or first balanced four-issuer count A=12. This is a projection pending the A=32 check. The quoted ≈EUR0.49 (B1−B2) and ≈EUR0.24 (B2−B4) compare **holder gas alone** at q0. Including shared costs allocated over four holders gives B1−B2≈EUR0.291 and B2−B4≈−EUR0.336. Preserve the sign and boundary; B4 is not the least total-cost design at A=4. Report shared and holder components alongside any per-holder allocation.

## 4. Gates in execution order

### G0 Define the question and freeze the evidence

Use protocol v0.3 and one common event ledger. Reconcile accepted K01–K16 definitions, quantities, units and actors. Preserve original raw inputs and manifests. Declare the admissible privacy/freshness set before evaluating financing. The signed control has a different privacy guarantee and shared-registry boundary; it is a diagnostic reference rather than a privacy-equivalent or minimum standalone implementation.

### G0a Early structural and economic go or no-go

This gate precedes new analytical development and EVM runs. Use archived gas splits and transparent projections in a small reproducible calculation. Vary absolute gas prices, for example q={0.01,0.1,q0,1,10,100}, with the historical exchange rate clearly labelled and varied separately. Start with measured A=4 and a frozen-coefficient A=32 projection. The N=16 anchor cannot literally contain 32 active holders; this projection is only a diagnostic. The real A=32 EVM run needs N≥32, for example N=128, with shared costs remeasured. Evaluate each admissible B set and common accounting boundary.

1. Verify the no-reversal implication and baseline `b_min(x;s)` frontier. A gas sweep alone cannot overcome the implication.
2. State a small set of independently motivated funding architectures. Derive minimum holder funding, sponsor support and initial liquidity. Use symbolic thresholds or ranges as outputs; do not force an outcome with the old EUR0.60/EUR4 caps.
3. Find whether a binding restriction can remove the minimum-resource design while another technically admissible design remains feasible. Distinguish a constructed example from a supported operational case. If a price threshold exists, report its assumptions and whether it persists under uncertainty. Otherwise report no reversal in the examined domain.
4. Separate the decision to continue the **design-reversal claim** from the decision to continue the **study**. Continue the former only with a justified constraint and a robust nonempty region. Continue the study on funding/liquidity/reliability frontiers only if those results answer a substantive new question beyond PUB-01 and ECON-07. Otherwise stop and reframe before the campaign.

No L2-specific claim follows until its full fee decomposition is supplied. A cheap scalar “L2 gas factor” is not a network model. The early gas-only pilot is a diagnostic test, not full lifecycle economics, observed demand or an EVM measurement.

### G1 Exact event replay and bounded expectation extension

Implement an independent event-state replay of all 54 archived scenarios. Require zero integer-count mismatches and exact recorded boundary behavior. Preserve the existing proof/receipt integrity checks as a separate validation layer. An expectation is not required to match each stochastic realization within ±1.

Extend and cite PUB-01's recurrence only where needed for the selected funding question. Validate stochastic expectations against independent simulated means and predeclared precision/confidence criteria. State horizon, access process, initial state, TTL, grace and population exposure. Record seeds, convergence and approximation limits.

For the first study, observed focal holders remain eligible over the ordinary workload. Their own revocation and reissuance economics are deferred; unrelated credential revocations drive invalidation. This conditioning is an explicit limit. Existing security tests for own revocation, stale roots, expiry, emergency invalidation, wrong group, replay and failed-state preservation remain required and unchanged. Deferring a workload does not weaken the protocol's denial rules.

### G2 Small model study and one active-wallet anchor

Keep B={1,2,4}, H=90 days and a short declared reference grid. Separate N issued credentials from A active holders and a=A/N. Because this version conditions all A focal holders to remain eligible, unrelated revocations must draw from a defined **non-focal revocable pool** N_u,g(t) in each group. Its event intensity is `λ_g(t)=κ N_u,g(t)` per day. A constant-exposure expected-count parametrization uses `κ=r/H`; applying that rate to a finite depleting pool is an approximation to that interpretation of r. For a finite credential with revocation probability p over H, use individual hazard `κ=−ln(1−p)/H` and decrease N_u,g(t) after revocation. State which process is used; do not silently reuse or replace a revoked credential.

For a balanced static non-focal pool, N_u=N−A if all A observed holders are excluded from revocation, giving the constant-exposure rate `r(N−A)/(BH)`. The shorthand `rN/(BH)` applies to an unconditioned full population, or an explicitly labelled approximation when A is negligible; it is not the exact rate for this conditioned workload. Constant exposure, finite depletion and any later replacement model must remain separate scenarios. Replacement economics is not part of the first version.

Use targeted model sweeps for r×δ and A×B, then only the uncertainty cases justified by G0a. Candidate r={0.005,0.01,0.02,0.05} per 90 days and TTL={7,30,60} are scenarios, not observed distributions. N=10⁴–10⁵, correlated incidents and heterogeneous issuers are optional follow-up work after a capacity/exposure model is specified, not required first-version deliverables.

Add **one A=32 EVM workload configuration**, balanced across four issuers, at an N within the current capacity, with the matched B=1/2/4/signed mechanisms and paired no-update controls. One anchor does not mean one transaction or one mechanism. Fix and record the reference access/publication schedule before running. Compare exact counts and receipt-based gas with the projection. Do not add A=64 to the initial campaign.

δ is grace after immediate authoritative publication, not publication batching. The current code caps δ at one day. δ={3,7,14} days is **model-only counterfactual work** for the first version: no contract change and no claim that the deployed implementation supports it. The model must preserve the first invalidating publication's deadline and clearly state its assumed semantics. Root-publication counts remain unchanged. Keep reporting delay outside the publication-to-rejection bound, and treat old-root proof admission separately.

The current four depth-10 trees hold at most 4096 credentials. Do not extend measured fixed-depth gas beyond capacity. Any future larger N scenario needs a larger-depth/sharding cost assumption, separately labelled.

### G3 Funding frontiers and conditional robustness

Use the reconciled event table for resource cost, payment routing, actor coverage and liquidity. Output `b_min(x;s,rule,timing)` or an equivalent set of nondominated funding vectors. Where actor budgets or support caps are uncertain, give ranges or threshold conditions rather than a single arbitrary success flag. Prior KYC outside the horizon and new issuance within it are separate cohorts; the latter can remain symbolic initially.

Off-chain prices require dated sources, service units, applicable volume/commitments and tax/currency treatment. A provider fee informs procurement cost, not holder willingness to pay. Price missingness must not become zero. Vary exchange rate separately from gas price. A reserve balance and its cost of finance must not be counted as the same expense.

For one named L2, Oleksandr supplies execution + L1 data + applicable operator fees under a dated network/version formula and transaction-data assumptions. Until that exists, mark the L2 frontier unavailable. Recheck the official specification when implementing it. Do not infer “never on L2” from the L1 gas sweep.

If G0a selects the reliability extension, connect grouping and grace to synchronized expenditure and compute trace-prefix liquidity at a fixed revenue, collection and refill schedule. This must extend the accepted ECON-07 compensation fund rather than repeat it. Compute the additional initial liquidity or funding required to meet a stated scenario reliability level or stress rule. Separate mean, quantile and worst-case claims. Monte Carlo uncertainty, parameter uncertainty and pricing uncertainty are distinct. This work reuses the validated simulator; it does not require more EVM configurations.

### G4 Scientific synthesis and release preparation

Generate fresh figures around the selected findings: (1) funding-frontier and no-reversal/constrained-regime comparison; (2) required holder/sponsor funding and active-population crossover; (3) grace/activity operating regions with model-only settings and the A=32 anchor marked; (4) liquidity or reliability premium, or conditional fee intervals if supported. Do not populate four figures merely to meet a count; combine panels when they answer the same question.

Perform an overlap check against PUB-01 and the accepted ECON-07 synthesis. Keep PRC and CRSet in related work. W3C Status List is a qualitative comparison by observer, disclosure, freshness, availability and trust, not local gzip milliseconds versus EVM gas. Build the bibliography by supported claims: accumulators/witness updates, ZK-KYC, EUDI/status infrastructure, ERC-4337/paymasters, service funding and uncertainty. Verify primary sources; a target number of references does not establish novelty.

Select the journal after the evidence and contribution are stable and current scope/indexing requirements are checked. No acceptance or fixed completion date is promised.

## 5. Responsibilities and immediate return

Oleksandr owns G0a, guarantee definitions, event semantics, model validation, the single new EVM anchor and technical fee inputs. Nataliya owns K01–K16 event mapping, sourced/symbolic off-chain prices, funding and liquidity conditions, and economic interpretation.

Her first return is a short note of about 2–3 pages and three simple templates, one worked example and missing inputs. The initial feasibility template has ten columns; measured gas quantities stay in the original summaries. The technical plan and evidence notes are optional reading. **Soft target: 30 November 2026; adjust together if necessary.** This is a planning target, not an imposed deadline or promise to complete all calculations.

The collaborator packet is self-contained for this checkpoint. Optional evidence notes and relevant images are included locally. Running the full experiment still requires the source recovery package; no required reading link depends on a GitHub push. Public code release remains a separate action.

## Primary sources for financing constraints

- [ERC-4337 specification](https://ercs.ethereum.org/ERCS/erc-4337): paymaster deposit and validation requirements; distinguish deposit from locked stake.
- [Pimlico sponsorship policies](https://docs.pimlico.io/guides/how-to/sponsorship-policies): examples of operation, user and aggregate policy limits.
- [OpenZeppelin paymasters](https://docs.openzeppelin.com/community-contracts/paymasters): operation authorization and funding conditions.

Recheck versions when implementing a concrete architecture. These examples do not establish the project's sponsor commitments or willingness to pay.
