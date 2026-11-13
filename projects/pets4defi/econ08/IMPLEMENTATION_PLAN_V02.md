# ECON-07 + ECON-08: implementation plan v0.2

Date: 13 November 2026. Status: **approved direction; new experiments and conclusions are not yet completed**. This document supersedes the research assignment in protocol v0.1. It preserves the accepted ECON-07 package and all archived ECON-08 measurements. The present checkpoint updates the plan and handoff; it does not implement the proposed campaign.

## 1. One question and a testable contribution

**For a specified issuer-hiding requirement and revocation deadline, which configuration `(B, δ, TTL)` minimizes lifecycle resource cost while admitting a payment allocation that covers each actor's costs and liquidity requirements, as credential revocation intensity and holder activity change?**

The candidate contribution is the joint *technical and financial feasibility boundary*. The study must show when payment constraints remove an otherwise economical technical design, how that boundary changes with population, activity, freshness and uncertain prices, and which actor pays. Payment transfers are not extra resource consumption. If feasibility constraints do not change any relevant decision, narrow the contribution accordingly; do not claim a new optimizer merely for plotting old grouping results.

Let `x=(B,δ,TTL)`, `z` denote workload, population and price assumptions, `C_i(x,z)` actor i's resource cost, and `t_ij` a payment from actor i to actor j. Minimize `Σ_i C_i(x,z)` over technical designs satisfying the stated privacy and freshness requirements **and for which some payment allocation exists**. For each actor, check net funding, coverage and the minimum balance along the event timeline. Internal transfers cancel in the aggregate. Fees, reserves, expected loss and cost of capital must each have a stated boundary; a reserve stock is not an expense.

This is a conditional design study, not evidence of demand, willingness to pay, adoption, market equilibrium, production readiness or profit. The signed control has a different privacy guarantee and the same shared registry boundary; it is a diagnostic reference, not the privacy-equivalent competitor or a minimal standalone signed implementation.

## 2. Novelty boundary against PUB-01

Use the reviewed PUB-01 manuscript (v7) as a predecessor and recheck section references against the final submitted version. Reuse no published/submitted figure. The following existing elements cannot individually be claimed as new.

| PUB-01 coverage | Already present | Required increment in this study |
|---|---|---|
| §3.5, Figure 3 | Finite-horizon authorization recurrence; expected counts versus update intensity; Poisson/grouping assumptions; TTL and activity examples | Exact replay of archived event semantics, followed by a validated extension for ordinary delay, separate activity and issuance populations, and explicitly bounded stochastic populations |
| §5 | Population-to-update link, including `λ=H·r` in that manuscript's notation | Consistent units and population process; rates tied to issued credentials, active users represented independently; depletion/replacement sensitivity |
| §4.4 | B=1/2/4 privacy, holder work and setup trade-off | Decision boundaries under privacy/freshness constraints and finite active populations; validate the projected setup/holder crossover |
| §3.6 and §4.6 | Actor cost shares and payment considerations | Event-level financial feasibility and liquidity constraints that can change the admissible design; evidence-backed prices and uncertainty propagation |
| Experimental figures | Grouping, workload and gas comparisons | New figures generated from the unified model/ledger; existing data used as labelled validation anchors only |

Draft novelty paragraph: “Building on the grouping and authorization-cost analysis of PUB-01, we study the feasibility of funding a credential-status service under explicit privacy and freshness requirements. We connect event-level resource quantities to actor payments and liquidity, and determine how feasible technical configurations change with the issued population, active participation, revocation process and uncertain prices. Archived traces validate the deterministic accounting; new, separately labelled experiments test selected extensions.” This is an intended contribution until the stated gates pass.

## 3. Frozen evidence and interpretation

- Archived evidence: 32 native scenarios and 22 four-wallet cohort scenarios; 8,832 ordinary accesses, 512 archived proofs (including 33 timing proofs), and 10,627 signed transactions. See [VALIDATION.md](VALIDATION.md) for evidence scope and checker results.
- Native pilot: one observed holder, two unrelated revocations. HIGH has B=1/2/4 authorization counts 5/4/3 at δ=0; at δ=24 h the counts are 4/4/3. The signed reference has 3.
- Cohort: four observed wallets, one per issuer, at issued populations N=16/128/512. Under N=16/HIGH/weekly, the per-wallet counts are 13/7/4 for B=1/2/4, and 3 for signed; totals are 52/28/16/12. Existing δ=0/1 h/1 day yield the same counts. Without updates each wallet has 3.
- The fixed weekly schedule has 12 publications regardless of N. Equal N=16/128/512 counts therefore do not estimate population scaling.
- Counters must distinguish total authorizations, initial authorizations, expiry/TTL renewals, revocation-triggered renewals and *excess versus a matched no-update control*. These are not interchangeable because renewal times shift TTL phases.
- Source measurements, proof/receipt archives, manifests and the accepted ECON-07 package remain unchanged. New results use new directories, run IDs and manifests.

## 4. Notation, semantics and population process

| Symbol | Meaning and unit | Required convention |
|---|---|---|
| H | Horizon, 90 days | Keep days/seconds explicit in every transformation |
| N(t), N_g(t) | Issued, currently eligible credential population; group population | Four issuer trees in the present implementation |
| A, a | Active holders and fraction A/N | N is not the number of measured wallets; state rounding and issuer allocation |
| B | Enforced issuer groups, 1/2/4 | Potential issuer sets 4/2/1 conditional on metadata, not anonymity entropy |
| r | Expected revocation count per credential over H in the constant-exposure model | If instead a probability of at least one event, label it p and convert hazard |
| μ_g | Group publication-event rate per day | Balanced constant exposure: `μ_g=r·N/(B·H)`; expected H-horizon count is `r·N/B` |
| δ | Ordinary cache invalidation delay after authoritative publication | Existing implementation permits at most 1 day |
| TTL | Authorization lifetime | Independent of credential expiry and publication delay |
| q, e | Gas price (gwei/gas), EUR/ETH | `EUR = gas · q · 10^-9 · e`; no reuse of λ for a gas multiplier |

If r is an expected count, the Poisson approximation assumes a process allowing replacement/reissuance or constant exposure. If p is a credential's probability of at least one revocation during H, a constant individual hazard is `-ln(1-p)/H`; it is not exactly `p/H`. A finite cohort revoked without replacement has decreasing eligible N(t) and each credential can leave at most once. Specify which process is simulated and compare it with the approximation. Own revocation stops eligibility until an explicitly modeled replacement credential is issued; distinguish that event from unrelated revocations. Reissuance adds issuance, witness and possibly admission costs, not only new exposure. Correlated issuer incidents are a separate sensitivity scenario.

At every access, process events in the documented order: publications precede accesses with the same timestamp; enforce credential validity and authorization expiry; then evaluate cached-authorization invalidation. The first invalidating publication sets the deadline. A later publication cannot extend it. A newly generated proof uses the current root; old-root proof grace remains zero in the archived setting and is distinct from δ. Expiry/own revocation must not silently become another successful authorization. Record rejected accesses and their cost separately.

δ does **not** batch root publications: the archived mechanism publishes immediately and tolerates an already cached authorization until its deadline. Multiple updates may share one subsequent renewal, but are still separate publications. If publication batching is later introduced, define a different parameter `τ_pub`, implementation and decision-to-rejection bound. Keep unmeasured reporting delay outside the guaranteed publication-to-rejection bound.

Current trees have depth 10 and capacity 1,024 credentials per issuer (4,096 overall). Model-only N=10^4–10^5 cases require an explicit larger-depth or sharding scenario and corresponding proof/publication/setup costs. Do not extrapolate the fixed-depth implementation beyond its capacity while retaining its gas figures as measured facts.

## 5. Incremental gates

### G0 — Freeze the question and common accounting (current document checkpoint)

Deliver the two-page protocol v0.2, this plan, a novelty matrix, economic handoff and templates. Reconcile K01–K16 with the accepted definitions before using labels in equations. Define events, units, allocation denominators and which uncertainties remain unresolved. No new empirical claim is introduced here.

### G1 — Deterministic event model on all 54 archived scenarios

Implement an event-state replay independent of the EVM runner. Consume archived access/publication timestamps, validity boundaries, group membership, TTL and δ. Recover per-wallet total and reason-specific counts, invalidation times, rejection decisions and a matched no-update counterfactual. Archive a machine-readable comparison.

Acceptance: **zero integer-count mismatches across all 54 scenarios** and exact boundary behavior for the recorded semantics. A tolerance of ±1 is not appropriate for deterministic replay. Any difference requires a documented modeling or data correction before further extrapolation. Keep current cryptographic/transaction integrity checks as a separate gate; successful byte verification is not evidence that a new analytical model is correct.

### G2 — Analytical expectation and stochastic validation

Derive the expected count for the defined state process, retaining finite horizon, TTL, δ, activity, initial state, expiry and own revocation. Reuse and cite PUB-01's recurrence where applicable. Identify exactly which extension requires a new derivation. Start with constant-exposure independent events, then test finite no-replacement and reissuance variants.

Validate expectations against repeated independent simulated traces using a predeclared confidence-interval/precision criterion, seeds and convergence report. Do not demand E[R] match each random realization within ±1. Compare stochastic model means and distributions; separately verify each deterministic simulator path against its state replay. Report assumptions under which closed-form approximations fail.

### G3 — Activity and scale, sparse design

Model candidate levels: N={16,128,512,4096,10000,100000}, a={0.01,0.1,1}, r={0.005,0.01,0.02,0.05} per 90 days, B={1,2,4}, TTL={7,30,60} days, δ={0,1 h,1 day,3,7,14 days}. These are a candidate pool, not a full Cartesian EVM campaign. State whether r is expected count or use the p notation/conversion above. Keep own-revocation/replacement and access-process scenarios identifiable.

Use one declared reference case, one-factor sweeps, selected pairwise interactions (r×δ, a×B, N×r), boundary cases and uncertainty samples. Set A explicitly, including A=4/8/12/32/64 where feasible, with a documented allocation across issuers. Cases with expected A below one need an explicit integer/population sampling convention. Large N is model-only until the capacity scenario is established.

EVM anchors: retain archived A=4; add selected A=32 and A=64 at an adequate N with four-issuer balance, fixed implementation capacity and matching activity/rate inputs. Choose points near a predicted crossover and one high-load point; avoid enumerating every grid combination on chain. Record exact authorization counts and receipts, plus correctness tests. New runs must not overwrite the archive.

### G4 — Extended δ, sequentially after baseline semantics

First validate the existing δ≤1-day contract and deterministic model. The current `MAX_DELAY=1 days` prevents deploying δ=3/7/14 as-is. Any extension requires a separate code change and review, followed by tests at first invalidation deadline −1/at/+1, later-publication non-extension, own revocation, credential expiry, TTL expiry, emergency invalidation and current-root proof admission. Only after these pass select a small EVM subset at δ=3/7/14. Plot reduced renewals separately from unchanged publication counts and increased stale-cache exposure.

### G5 — Unified economic and L2 scenarios

Use one versioned event table as the input for both ECON-07 tariff calculations and ECON-08 technical comparisons. Replace the old HIGH=13 assumption with scenario-specific actual counts; retain old calculations as frozen historical evidence. Reconcile actor categories with K01–K16 and the boundary before monetization. Obtain sourced off-chain prices, retain unknown entries, and vary hypothetical budget caps independently of procurement prices.

Use absolute q levels, for example {0.01,0.1,1,10,100} gwei/gas, plus the historical reference q0=0.130658648 gwei/gas and multipliers {0.1,1,10,100,1000} for transparent sensitivity only. Label these scenario levels, not measured market frequencies. Vary e separately and report price/source/date/network. Do not present the old combined multiplier as a gas price with stable units.

For one named L2, calculate execution fee + L1 data fee + any applicable operator fee using the documented network/version formula and actual transaction data. Archive chain/block/time, fee parameters, calldata/compression assumptions and exchange rate. Retain any costs that do not follow the L2 gas-price change. A scalar “L2 is x times cheaper” is insufficient. The OP Stack fee documentation is a candidate model specification; confirm it at implementation time.

For each design, compute total resource cost, cost incidence, internal payments, fee bounds, coverage and required liquidity/reserve over time. Report when no feasible tariff exists under the stated budget caps. Distinguish purchase price evidence from willingness to pay and give threshold sensitivity where evidence is absent. Pass only when every monetary result has quantity, unit price, source/scenario flag, denominator and boundary.

### G6 — Publication package

Write the methods from the validated protocol; move implementation caveats to a focused Limitations section without hiding assumptions. Generate fresh figures, an auditable common event table, price provenance and reproduction commands. Perform a final overlap check against PUB-01. Select a journal after confirming current scope, article requirements and indexing from authoritative sources; the proposed venues are candidates, not a verified ranking claim.

## 6. Anchors to audit, not final conclusions

At N=16, A=4, HIGH, weekly and δ=0, measured total gas is 56,430,653 for B=1 and 46,253,913 for signed. Difference: 10,176,740 gas for the four-wallet cohort. At the historical ECON-07 reference q0=0.130658648 and e0=2,164.73 EUR/ETH, this is **EUR 0.719599 per active wallet per 90 days**, dividing by 4, not 16. The reference is conditional and not a current market quote. With no updates the corresponding B1−signed difference is negative (−1,338,004 total gas); higher gas prices materially change the magnitude. “Privacy is cheap” or “KYC dominates” is therefore a hypothesis to test, not an established universal result.

Under linear replication of the measured four-holder workload, shared gas plus per-holder gas gives:

| B | Projected total gas G_B(A) |
|---|---|
| 1 | 13,817,033 + 10,653,405 A |
| 2 | 16,592,944 + 8,930,165 A |
| 4 | 24,791,056 + 8,068,512 A |

B4 and B2 intersect at A≈9.5144 (first integer 10, or 12 if all four issuers must have equal active populations). This is a conditional projection with fixed shared workload, not a measured 10-holder result or a universal minimum. Validate it at new active-wallet anchors. Publish all pairwise comparisons, privacy feasibility and alternative schedules; no-update and sparse-activity behavior can change the choice.

## 7. Figures and literature

1. Renewal burden versus grace δ and active workload, with revocation rate as a scenario or facet; distinguish model curves, uncertainty and EVM anchors. State whether the ordinate is total, revocation-triggered or excess renewals. Do not reproduce PUB-01 Figure 3's expected-count-versus-rate plot.
2. Lifecycle cost and partition break-even versus active-holder count A, with grace scenarios and shared/publication/holder components separated; include the unchanged-renewal region and explicit freshness interpretation.
3. Privacy requirement × deadline decision map: admissible B, resource-cost minimum, and payment-feasible region (including infeasible cells). Show active-holder crossover in an inset or companion panel.
4. Updated fee/tariff intervals and coverage/reserve boundaries from the common ledger and stated prices; display empty intervals and uncertainty.

Keep PRC out of the experimental campaign; CRSet belongs in related work. Compare W3C Status List qualitatively by observer, disclosure, freshness, availability and trust assumptions. Historical local W3C gzip/millisecond results are archived component observations, not a gas comparison. They are excluded from the active economic handoff.

Build the bibliography by claims, targeting adequate coverage rather than padding to a count: dynamic accumulators and witness updates; ZK-KYC (zkMe, Privado/iden3, ZEBRA); EUDI revocation/status infrastructure; W3C status lists; ERC-4337/paymaster sponsorship; economic service funding and uncertainty. Verify primary papers, current official specifications and price pages. PUB-01 remains the direct predecessor. A 30+ source target does not substitute for a supported novelty claim.

## 8. Responsibilities and immediate handoff

**Oleksandr:** technical semantics, novelty comparison, model/trace validation, implementation/capacity changes, sparse EVM campaign, guarantee comparison and scientific figures. **Nataliya:** accepted K01–K16 definitions mapped to events and actors, unit-price evidence/scenarios, cost/payment allocation, coverage/liquidity and conditional fee bounds. No cryptographic observer, PRC implementation or proof-security review is assigned to Nataliya.

Her first deliverable is a **2–3 page economic note plus three populated templates**, with one worked N=16/A=4/HIGH/weekly/δ=0 comparison and an explicit missing-input list. Do not build a complete economic model before technical event definitions and quantities are reconciled. Instructions and template field meanings are in [handoff/START_HERE.md](handoff/START_HERE.md).

## 9. Completion evidence for this checkpoint

- Plan v0.2, protocol v0.2 and active task descriptions agree on scope, counts, boundaries and ownership.
- Accepted ECON-07 and original ECON-08 result files retain their bytes; checksum comparisons document preservation.
- The active handoff ZIP includes protocol v0.2, this implementation plan, the two original native/cohort summaries, instructions and three templates; v0.1 and W3C component timings are labelled historical and excluded.
- No new experiment, expectation-validation result, L2 fee result or accepted K mapping is claimed as completed.
- Commit/push/publication are separate actions after review of the concrete local change.
