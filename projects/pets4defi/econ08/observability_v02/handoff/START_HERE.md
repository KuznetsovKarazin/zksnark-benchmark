# Your next economic task for ECON 08

Nataliya Kolyada and Oleksandr Kuznetsov. Technical pilot v0.2, economic handoff revision 2, 16 November 2026.

**Please prepare a 2–3 page economic note and one completed payment table. Start
with weekly A=4; use asymmetric A=32 to compare the three allocation rules against SELF. Soft
target: 30 November 2026, adjustable to your availability.** You do not need to
review cryptographic code, rerun EVM measurements or redo the accepted ECON-07.

## How the pieces fit together

PUB-01 showed that a revocation can make holders of other issuers authorize again.
ECON-07 supplied lifecycle accounting and the distinction between costs, payers
and transfers. Your ECON-08 addendum v0.2.1 showed that the funding-pool benefit is
small in the supplied cases and retained capital is not gas expenditure. That
conclusion remains valid; we are not asking you to find a larger pooling benefit.

The new technical pilot studies why this extra work may be necessary. If a public
observer can distinguish a full authorization from a cached access and can label
issuer publications, reacting only to one's own issuer can reveal that issuer.
Within a precisely specified cache model, common invalidation minimizes access gas
under perfect hiding. A probabilistic alternative saves some gas but leaks some
information. This is a modeled boundary, not a claim about every credential system.

**Your question is who bears the resulting externality, and how issuer-funded or beneficiary-funded
allocation changes its incidence.** The gas is still consumed; reimbursement
only moves its financial burden. Publication/setup costs stay outside this small
access-only comparison and retain their earlier lifecycle entries.

## Inputs already supplied

1. [economic_cases.csv](../results/economic_cases.csv): 12 short rows, common and
   selective references plus two randomized cases, A=4/32. A is active holders,
   not issued population N. A32 is modeled, not a new EVM measurement.
2. [payment_comparison_REFERENCE.csv](payment_comparison_REFERENCE.csv): actor
   costs and compensation already computed in gas-equivalent units. Complete the
   euro conversion and economic interpretation in a copy; do not hand-enter the
   technical quantities again.
3. [price_inputs.csv](price_inputs.csv): the same historical q0/e0 references you
   already documented, with x10/x100 as hypothetical common price multipliers.
4. [compensation_reference.csv](../results/compensation_reference.csv) and
   [coalition_costs.csv](../results/coalition_costs.csv): optional audit detail.
   The latter contains all 96 subset comparisons; the first checkpoint does not
   require recomputing every Shapley value by hand.

## Fixed rules for this comparison

* **SELF:** holders pay their own access gas; no compensation.
* **Publication frequency:** for each holder group, foreign issuers fund its net
  extra access cost in proportion to their publication counts.
* **Shapley externality:** split the same net extra cost by the supplied average
  marginal cost of adding each foreign issuer's publications, across all orders.

We have fixed these reference rules so the results are comparable. The two issuer-funded compensation
rules balance before monetary rounding. Their total reimbursement is the
same; the distribution among issuers can differ. Neither rule has been proved
incentive-compatible or commercially acceptable.

* **Beneficiary pays (equal per holder):** treat issuer hiding as a shared benefit
  and divide the total common-minus-selective premium equally among all active
  holders in the public group. This is an equal-share normative benchmark; it
  does not establish equal benefit valuations or willingness to pay. Let E be
  the total premium, A the active-holder count and A_g the count in issuer group
  g. Its final burden is C_selective,g + A_g E/A. Issuers pay no reimbursement.
  Holders initially pay their actual common-policy access gas. The table records
  only the net settlement needed to reach that allocation: a group pays
  max(A_g E/A - E_g, 0), or receives max(E_g - A_g E/A, 0), where
  E_g = C_common,g - C_selective,g. The intermediary retains zero net funds; its
  implementation/settlement overhead remains unknown. Fractional allocation
  balances exactly before display or monetary rounding.

There are now **four alternatives: SELF plus three allocation rules**, with
96 actor rows and 12 case/rule comparisons. The beneficiary rule is defined
over all A=4 or A=32 holders, not separately within each issuer subgroup. The
technical observer and all 26 pilot result files are unchanged.

## Concrete first return

1. **Check one worked case.** In weekly A=4, common minus selective is 10,373,004
   gas for four holders over 90 days, or 2,593,251 per holder. Common costs 32.33%
   more than selective; selective saves 24.43% relative to common. These have
   different denominators. Convert with EUR/gas = q_gwei × 10^-9 × EUR/ETH.
2. **Complete the payment table.** For SELF and all three allocation rules, distinguish
   resource expenditure, reimbursement paid, reimbursement received and net burden
   of each issuer and holder group. Show that transfers do not change aggregate
   resource cost. Check the historical reference and the two price sensitivities.
3. **Interpret the asymmetric case.** Compare who pays under the three allocation rules against SELF. Discuss
   budget balance, symmetry, zero marginal effect, auditability and administrative
   effort. Explain why counting publications can charge an issuer differently from
   measuring its marginal effect when updates overlap or TTL changes the schedule.
4. **State the incentive limit.** A fee based on revocations/publications could make
   prompt reporting privately costly. Contrast this direct publication-dependent charge with the beneficiary
   benchmark, which has no direct issuer levy. Its aggregate premium can still
   depend on the publication schedule, so indirect pass-through or coalition
   incentives remain possible. Explain what governance or enforcement would
   be needed before calling a rule sustainable. Do not assume issuers may
   safely suppress revocations. Do not infer willingness to pay from KYC prices.

**Two required interpretation checks.**

* In symmetric weekly A=4, each issuer pays 2,593,251 gas equivalent under either
  issuer-funded rule and its own holder receives 2,593,251. The net transfer is
  zero after consolidating each issuer with its affiliated holder. Issuer and
  holder are distinct actors: their individual burdens change. Under beneficiary
  pays, no net settlement is needed and the outcome coincides with SELF. This
  symmetry is a useful control; the asymmetric case carries the distributional
  comparison.
* State the reference order of magnitude in the conclusion: about **EUR 0.73 per
  holder over 90 days**, or EUR 2.93 for four holders. The x10/x100 scenarios are
  sensitivities, not current prices or forecasts. No commercial materiality or
  willingness-to-pay conclusion follows from these amounts alone.

Deliver the note, completed table and a short missing-input list on the existing
[ECON-08 card](https://trello.com/c/8i08gLxj). Please link one versioned package.

## Scope and responsibility

Oleksandr owns the observer model, proofs, event timing, coalition inputs and gas
coefficients. The supplied new-policy costs use common archived B1 coefficients;
they are not receipts from a new selective-cache contract. The reference prices
are historical, not current quotes. Reimbursement settlement gas, overhead, real
issuance costs and the monetary value of denied access remain unknown. Keep those
separate or symbolic; do not set them to zero in a full lifecycle conclusion.

The [model](../MODEL.md), [proofs](../proofs/CONDITIONAL_RESULTS.md), clustering
results and full research report are **for information only** for this checkpoint.
No new paymaster calculation, new contract, literature survey or full manuscript
is requested. The earlier liquidity addendum remains a completed, separate result.
