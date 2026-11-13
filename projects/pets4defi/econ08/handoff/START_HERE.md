# Your first economic task for ECON 08

Nataliya Kolyada and Oleksandr Kuznetsov. Version 0.4, 13 November 2026.

Please prepare a short note of about **2–3 pages**, a first pass through the three starter tables, and one worked comparison. **Soft target: 30 November 2026; we can adjust it together.** A clear list of missing inputs is a useful part of the first return.

## How this follows the previous work

**PUB-01** counted authorizations and measured gas costs when credentials share a privacy mechanism. **ECON-07** extended the accounting: which expenses occur, who pays them, and which payment arrangements cover costs. Both remain prior work.

**ECON-08 now asks about the money needed at a particular time.** A revocation can invalidate cached permissions for other holders in the same group. Those holders renew only when they next access the service. If several return before an account is refilled, their payments may require more cash than an average-cost calculation suggests. We will test whether that effect exists and matters; we have not assumed the answer.

## Two rules already fixed for the comparison

You do not need to choose the baseline payment rules. Use these two:

| Rule | Who pays for holder operations | Who pays shared costs |
|---|---|---|
| SELF | Each holder pays from their own funded wallet. | Operator and issuers pay their own deployment/publication costs. |
| PM | One prepaid account pays the covered operations of all observed holders. | The same shared operator/issuer costs stay outside this account. |

PM is a paymaster-inspired model of funding. The first calculation uses the existing direct-operation gas as a proxy. It does not measure a new paymaster implementation or its extra fees. Covered holder operations include the four approvals and 400 accesses in the worked cohort; transferred asset principal is not a gas expense.

For both rules, use the same fixed clock: funding at the declared start, then restoration to the target balance every 24 hours **before** any operation at the same timestamp. Apply that clock to the SELF wallets and shared accounts as well as the PM account. Weekly refill and no refill are later sensitivity checks. Exact timestamps and definitions are recorded in [FINANCING_RULES.md](FINANCING_RULES.md).

## What to do first

1. **Map the costs.** In [ledger_mapping_TEMPLATE.csv](ledger_mapping_TEMPLATE.csv), keep the accepted K01–K16 definitions. Link each relevant event to its quantity, unit, source, resource-bearing actor and payer under SELF/PM. Split a row only when the payer or meaning differs. Deposits and top-ups transfer money; they do not create a second resource expense.

2. **Check prices.** In [price_assumptions_TEMPLATE.csv](price_assumptions_TEMPLATE.csv), record dated evidence or leave an input unknown/symbolic. Historical q0=0.130658648 gwei/gas and e0=2164.73 EUR/ETH are supplied references, not current quotes. Provider KYC prices do not show willingness to pay. Oleksandr supplies L2 and any account-abstraction overhead inputs.

3. **Explain the funding comparison.** In [feasibility_TEMPLATE.csv](feasibility_TEMPLATE.csv), use the prefilled SELF/PM cases. For each funded account, record the target balance, later top-ups, final unused balance and actual resource expense. The supplied target is a floor from observed payments, not a safe deployment reserve. Start with B=2 and its no-update control; other prefilled rows can remain for later. Name the actor and denominator. Shared costs remain separate from the pooled holder-operation account.

Start with N=16 issued credentials, A=4 active holders, HIGH activity, weekly updates, δ=0, over 90 days, and the matched no-update control. Original [cohort_summary.csv](cohort_summary.csv) gives aggregate quantities; [pilot_summary.csv](pilot_summary.csv) describes the separate one-holder pilot. The [timed summary](optional/liquidity/liquidity_summary.csv) and [account table](optional/liquidity/liquidity_accounts.csv) supply the first worked comparison. Aggregate gas alone cannot reveal the maximum daily funding requirement. In this initial replay, startup determines the full-lifecycle daily and weekly holder funding target, which is almost identical across the three ZK groupings; the scientific gate remains open.

For orientation, weekly authorization totals for B1/B2/B4/signed are 52/28/16/12 across all four holders. No-update totals are 12 for each. The signed reference has different privacy. B denotes grouping, δ is the allowed delay after publication, and TTL is the cached authorization lifetime; Oleksandr owns those technical definitions and correctness checks.

## What the note should say

Explain whether SELF and PM change **who must have funds available**, how much is needed before the next refill, and how this differs from total 90-day expense. A no-refill account with only debits needs enough to cover the full cumulative debit; that equality is a control, not proof of a funding burst. Do not label a transfer or unused balance as an expense.

Use required funding as the output. You do not need to choose arbitrary holder budgets or find a constraint that forces a different preferred design. Report a missing timed input precisely instead of inferring it from a total. A familiar payment rule does not by itself show that the new research question has a useful result.

Read the [two-page protocol](ECON07_08_Research_Protocol_v0_4.docx) for context. The [detailed plan](optional/IMPLEMENTATION_PLAN_V04.md) and [technical evidence notes](optional/README.md) are **for information only**. All reading files are included in this ZIP; no software installation or GitHub access is needed for your first task. Do not repeat the accepted ECON-07 study or review cryptographic code.

Post the note, first tables and missing-input list on [ECON-08](https://trello.com/c/8i08gLxj). Oleksandr owns the early scientific check, timed-event model, validation and any further measurements. This packet does not claim new EVM measurements or a completed paymaster experiment.
