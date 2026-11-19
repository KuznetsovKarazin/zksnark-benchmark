# Research plan for revocation induced liquidity needs

ECON-07 + ECON-08, version 0.4, 13 November 2026.

**For information only for Nataliya.** Her first task is in `handoff/START_HERE.md`. The payment rules are already fixed in `handoff/FINANCING_RULES.md`; she is not being asked to select a cryptographic architecture or invent the baseline financing assumptions. This plan supersedes v0.3 as the active research plan. Accepted ECON-07 and the original technical measurements remain prior evidence.

## 1 Central question and potential contribution

**How does a revocation affecting one credential change the near-term funding required by other active holders or a prepaid account that pays for their operations, under fixed collection and refill schedules?**

The candidate contribution is a *liquidity spillover*: shared status changes can cause several otherwise eligible holders to need new authorizations, and their later accesses may concentrate expenditure within the same funding interval. This is a hypothesis to test, not a result assumed from the architecture. Renewal occurs at the holder's next access requiring it, not automatically when a revocation is published. A common update therefore need not produce simultaneous cash demand.

PUB-01 studied authorization counts, timing, grouping, TTL and resource gas costs. Accepted ECON-07 developed lifecycle accounting and payment/fund conditions. The proposed increment connects the same technical state transitions to a timed payment ledger under specified funding rules. The result must show whether total expense and short-term liquidity behave differently, and which timing or grouping conditions explain that difference. Counting the same costs again or multiplying them by gas price is insufficient.

| Research question | Required output | Boundary of a possible contribution |
|---|---|---|
| RQ1. Is there a liquidity spillover? | Compare paired update and no-update paths under the same accesses and fixed payment/refill rule. Measure the extra funding needed before the next refill and identify who must provide it. | A positive difference needs to be traced to actual event ordering; a group publication alone does not establish a burst. |
| RQ2. When do funding peaks differ from total costs? | Report total net expenditure, maximum interval funding and their ratios/differences across B, activity phase and refill interval. | The no-refill case is an accounting control: with only debits its required deposit equals cumulative expenditure. It is not evidence of a burst-specific effect. |
| RQ3. Who bears the funding requirement? | Compare direct self-payment with a prepaid holder-operation account, while keeping shared operator/issuer payments separate. Give holder and account funding requirements as outputs. | This is a change of payment location and timing. It does not reduce aggregate resource consumption or demonstrate market willingness to pay. |
| RQ4. Does the effect persist under plausible variation? | Test access phases, daily versus weekly refill, TTL/grace and bounded price/workload uncertainty. Add tail funding only after deterministic effects are established. | A substantive operating-region or uncertainty result can support the paper. A mechanically constructed cap or a trivial rescaling cannot. |

G0a decides whether these questions support a distinct article. A familiar or standards-motivated funding rule makes a scenario understandable; it does not prove the scientific effect or automatically pass the gate.

## 2 Fixed financing rules

The canonical rules and timestamp conventions are in [FINANCING_RULES](handoff/FINANCING_RULES.md). All calculations, templates and figures must use that file, with its version recorded.

| Rule | Holder operations | Shared deployment and publications | Interpretation |
|---|---|---|---|
| SELF | Each holder pays the costs assigned to that holder's operation stream. | Operator and issuers pay their own shared cost streams, recorded separately. | Direct-payment reference; no fictitious transfer between holders is assumed. |
| PM | A prepaid account funds the holder-operation stream specified in FINANCING_RULES. | Remain outside the prepaid account and are paid by operator/issuers. | A paymaster-inspired funding model, using a direct-gas proxy initially. It is not a measured ERC-4337 implementation. |

The primary refill interval is 24 hours. Seven-day refill and no refill are sensitivities. The common origin is `report.context.base − 3600`, the fixture initialization time before setup; first access occurs one hour later. Fund initially at that origin and restore each target balance at `t0 + kΔ` before operations sharing that timestamp. Use this same grid for every B, each SELF holder and shared account, and PM. The PM stream includes four approvals and 400 accesses, including full authorizations and cache hits, and excludes asset principal. Each account is funded by its specified treasury. Baseline refills are ideal, free and instantaneous, without customer collections, refunds or reimbursements. Do not optimize each design's refill phase after viewing results.

Deposits, top-ups and reimbursements move funds; they are not additional gas/resource expenses. The maximum observed interval debit is a hindsight spending floor under these assumptions, not an ERC-4337 validation deposit or an estimated future reliability guarantee. Report initial funding, later treasury top-ups, cumulative funding and ending balance separately: target stock is not total treasury obligation. Any cost of capital is a separately sourced or symbolic assumption. Report shared costs beside the account stream so a cheaper-looking holder payment does not hide expenses moved elsewhere.

The v0.3 `operator_only_sponsor` example funded shared operator costs while forbidding holder-to-operator transfers. It was a constructed existence diagnostic. **It is not the PM rule, not a standard paymaster architecture, and not evidence that a real sponsor budget binds.** It remains archived historical material and cannot be used as the new baseline.

## 3 Quantities and accounting tests

For every actor/account, construct a timed ledger with debits for included resource payments and credits for the prescribed funding/receipts. With fixed receipts excluding initial prefunding, minimum initial prefunding is the largest positive cumulative net debit over event prefixes. Preserve event order at equal timestamps. Once replenishment is specified as a balance restoration, apply that rule to each refill interval; do not count restored funds as a second resource cost.

Report separately:

- Total 90-day resource cost, split into holder operations, shared deployment/publications and any measured extra implementation overhead.
- Required initial deposit or prefunding for each actor/account under the fixed rule.
- Maximum debit requirement between scheduled refills, its event interval and the events responsible.
- Difference from the matched no-update path, retaining the same access timestamps and refill schedule.
- Funding shortfall for an illustrative available balance only as a sensitivity after required funding has been calculated.

With no credits and no refill, cumulative net debit is monotone and required prefunding equals the final cumulative debit. With credits, use the largest prefix net debit; final net expense alone may be smaller. Neither case should be relabelled a burst statistic without an interval/refill comparison. A stock of deposited money is not the sum of repeated transfers into the account.

For an aggregate PM stream, simultaneous or nearby holder operations can increase interval requirements. Pooling may also reduce a sum of separately reserved maxima when holders peak at different times. Determine which occurs from the traces. A claim that pooling always worsens or always improves liquidity is not assumed.

The earlier unrestricted-transfer no-reversal result remains an accounting baseline: if aggregate financing is identical, transfers are free and timing has no effect, a minimum-resource design cannot be uniquely excluded while a more expensive one is financed. It is an elementary reference, not the candidate contribution. The present study holds timed rules fixed and does not search for arbitrary constraints that force a design reversal.

## 4 Existing evidence and limits

Preserve the original 32 pilot and 22 cohort scenarios, 8,832 ordinary accesses, 512 saved proofs including timing observations, and 10,627 signed transactions including shared setup, updates and diagnostics. Cohort N=16/128/512 is issued credentials with four measured active wallets. The twelve weekly publications do not scale with N, so those existing cases do not establish population scaling.

For N=16/A=4/HIGH/weekly/δ=0, total authorizations are 52/28/16/12 for B1/B2/B4/signed, compared with 12 for each in the no-update cases. Count full authorizations, reason-specific renewals and excess versus control separately because renewal timing can shift TTL phases.

The historical price anchor q0=0.130658648 gwei/gas and e0=2164.73 EUR/ETH is not a current market quote. Gas quantities should be analyzed before monetization. The v0.3 corrections remain valid: ≈EUR0.49 and ≈EUR0.24 compare direct per-holder gas alone; including shared costs allocated over four holders gives B1−B2≈EUR0.291 and B2−B4≈−EUR0.336. None of these terminal quantities measures the size of a daily funding peak.

The initial PM calculation maps observed direct holder-operation gas to a hypothetical prepaid stream. Additional account-abstraction validation, EntryPoint execution, paymaster processing, post-operation work and funding-transaction costs are **not measured** by those traces. Label outputs as a proxy. Do not call the difference between SELF and PM measured paymaster efficiency. Add symbolic/explicit sensitivity for unmeasured overhead or defer absolute implemented PM costs until measured.

## 5 Execution gates

### G0 Freeze rules and common events

Pin the v0.4 protocol, FINANCING_RULES and event categories. Reconcile K01–K16 without changing accepted definitions. Identify the existing timestamp/receipt fields required to build each stream, the fixed prices for the diagnostic, and the matched no-update controls. State the admissible privacy/freshness set independently of financing.

### G0a Test the liquidity hypothesis before the campaign

Start with the archived four-holder traces. Apply SELF and PM exactly as specified, first using 24-hour refill, then seven-day and no-refill controls. Reconstruct renewal times at actual next accesses. Produce an auditable event table and actor/account prefix balances. Explain any cases where a publication does not cause immediate renewal, a grace change leaves counts unchanged, or expiry shifts later renewals.

**Initial v0.4 diagnostic:** eight existing matched traces have been replayed without a new EVM run. For the primary 24-hour and seven-day schedules, the full-lifecycle holder target is almost identical across B1/B2/B4 (a 108-gas range across the six ZK update/control traces): startup spending dominates the maximum. Descriptive post-startup differences do not change that primary result. G0a therefore remains open, and the diagnostic does not authorize a broad campaign. The next bounded study must predeclare startup versus continuing-service reporting and matched access/TTL phases, retaining the full-lifecycle result and both positive and negative differences. It must not search for timing conditions solely to force an effect. Exact quantities and accounting checks are in the optional timed diagnostic.

The gate passes only if a nontrivial, reproducible difference in interval funding, peak location, cost-versus-liquidity ranking or a clearly bounded operating region provides an additional result beyond PUB-01/ECON-07. Confirm that it is not caused by inconsistent setup allocations, time-zero ordering, post-hoc refill choices, an arbitrary sponsor cap or a proxy/implementation mismatch. Show sensitivity to at least the declared refill alternatives and one access-phase control when data permit.

If the first traces produce only cumulative-cost restatements, record that outcome and revise the hypothesis before new EVM work. Standards motivation alone is not a pass. A nonzero number alone is not sufficient; report its scale relative to total and ordinary operating requirements and what assumption makes it useful. Do not invent a numerical materiality threshold after seeing the result.

### G1 Validate the event model

Independently replay all 54 archived scenarios with exact integer counts and boundary decisions. Preserve existing proof/receipt integrity checks as a separate layer. Validate stochastic extensions, if selected, against independent simulated means and confidence intervals rather than requiring E[R] to match each random trace within one event.

Observed focal holders remain eligible in the first ordinary workload. Their own-revocation/reissuance economics is deferred, but existing rejection tests for revoked credentials, stale roots, expiry, emergency changes, wrong groups, replay and protected-state preservation remain required.

### G2 Focused model study and one EVM anchor

Keep B={1,2,4}, H=90 days and a short declared reference workload. Separate issued N from active A. Because all A focal holders are conditioned to remain eligible, unrelated revocations draw from a non-focal pool N_u,g(t). Use `λ_g(t)=κN_u,g(t)`, with a clear expected-count rate or a probability-based individual hazard. For balanced static non-focal exposure N_u=N−A, the expected-count parametrization is `r(N−A)/(BH)`, not the unconditioned `rN/(BH)`. Finite depletion and any constant-exposure approximation must be labelled; no silent replacement is permitted.

Use model sweeps tied to the funding question: access phase/activity, B, TTL and grace relative to the fixed 24-hour refill clock. The seven-day and no-refill cases remain sensitivity controls. Candidate revocation levels 0.5/1/2/5% per 90 days require the count-versus-probability convention before use. Large N, correlated incidents and heterogeneous issuers are optional follow-up work.

One new A=32 EVM workload configuration is planned, with matched B1/B2/B4/signed mechanisms and no-update controls, at N≥32 within the current capacity; N=128 is a feasible candidate. One anchor means a matched family of runs, not one transaction. Freeze the workload before execution and remeasure shared costs. A=32 projected from N=16 coefficients is a diagnostic extrapolation, not an N=16/A=32 deployment.

δ is post-publication grace, not root-publication batching. Renewals wait for a qualifying access; later updates cannot extend the earliest invalidation deadline. δ=3/7/14 days remains model-only in this version; the implemented cap stays one day. A64 and contract changes are deferred. The four depth-10 trees hold at most 4096 credentials; larger populations require an explicit capacity and cost model.

### G3 Economic interpretation and optional stochastic risk

Nataliya uses the same measured event quantities and fixed rules to calculate required holder funding, PM deposit/top-ups and shared operator/issuer funding, keeping credits and expenses separate. Off-chain prices need dated sources, units, volume/commitments and tax/currency treatment, or remain symbolic. Provider prices do not establish willingness to pay. Previously verified holders and new issuance inside the horizon remain different accounting cohorts.

Oleksandr supplies one documented L2 fee model with execution, L1 data and applicable operator fees. Until available, label L2 results unavailable; do not substitute an arbitrary multiplier or infer the absence of an L2 effect from an L1 gas sweep. Any claim about actual paymaster costs also requires the missing implementation overhead.

After a deterministic effect is established, consider tail funding under a specified stochastic access/revocation process and fixed refill rule. Distinguish expected expense, funding quantiles, worst-case bounds and Monte Carlo uncertainty. This extension should reuse the validated simulator rather than trigger a large EVM grid.

### G4 Scientific synthesis

Candidate new figures are: paired event/prefix-balance traces showing when a shared update causes spending; total cost versus required interval liquidity across B and refill intervals; activity/grace operating regions with model-only cases and the A32 anchor marked; actor funding incidence or a validated tail-funding result. Select figures only after G0a. Reuse no submitted PUB-01 figure.

Compare explicitly against PUB-01's recurrence/timing/grouping results and ECON-07's compensation-fund accounting. The new relation must be technical grouping/grace and actual access times to cash needs under the fixed SELF/PM rules. Keep PRC/CRSet in related work and W3C in a qualitative guarantee table. Maintain primary-source evidence for sponsorship mechanics, without equating the documented existence of a mechanism with evidence for the numerical result.

## 6 Responsibilities and first return

Oleksandr owns the financing-rule specification, technical guarantees, timed event extraction, G0a, validation and new measurements. Nataliya maps accepted K01–K16, sources prices, computes and explains the fixed-rule funding requirements, and flags exact missing inputs. She is not asked to choose the baseline rules or review cryptographic code.

First return: a short note of about 2–3 pages, the three prefilled starter templates, one worked comparison of SELF and PM and a missing-input list. All templates retain ten columns. The plan and deep evidence notes are for information only. Soft target: 30 November 2026, adjustable together.

The active packet is self-contained for reading. Code publication and experiment execution are recorded separately; a working link or a completed push does not mean G0a passed or that new measurements exist.
