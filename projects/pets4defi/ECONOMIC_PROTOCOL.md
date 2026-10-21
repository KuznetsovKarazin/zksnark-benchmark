# Economic protocol: private access, cost sharing and service coverage

Owner: Nataliya. Technical contact and reviewer: Alexander. Start with ECON-03; implementation and sensitivity results follow in ECON-04/05. No calendar deadline is set here.

## Question and comparison

For one matched deposit service, how do repeated use, credential validity and revocation requirements affect the external cost of eligibility checks? Under a stated fee and cost-sharing rule, what additional user benefit and service margin would cover those costs?

The five technical methods are unchecked, signed direct/cache and ZK direct/cache. At each workload select signed and ZK modes by minimum **user action and approval gas before any subsidy**. Retain both technical alternatives in the data; this selection is not a minimum over total service costs.

| Economic regime | Technical implementation | User share of allocation pool |
|---|---|---|
| B0 | Selected signed method | 1, held fixed |
| B1 | Selected ZK method | 1 |
| B2 | Same selected ZK method as B1 | 0, 0.25, 0.5 or 0.75 |

The alpha=1 endpoint of the private sweep is B1, not an additional distinct B2 case. The unchecked deposit is a cost reference, not an equivalent compliance service. Hold the eligibility rule, deposit function, amount, investment return and risk assumptions fixed. Only the declared privacy/access and financing differences enter the comparison. Public wallets, amounts and transaction timing remain visible.

## Event and payment ledger

Use [event_ledger.csv](data/event_ledger.csv) as the starting interface. Each priced line needs its event, trigger/count, executor/payee, initial payer, final cost bearer, amount/unit, date/source, and invoice overlap. Counts supplied by the model are synthetic; measured gas does not make those frequencies observed data.

For each regime j, use one currency and the same 90-day horizon:

- A_j: explicitly declared shareable external access-cost pool per user.
- u_j and s_j: other variable external expenses paid by the user and service respectively, excluded from A_j.
- alpha_j: user share of A_j; the service pays the remaining share.
- f_j: fee transferred from user to service per user over the horizon.
- m_j: other net service revenue per user over the horizon, excluding f_j and after unrelated costs.
- F_j: fixed service expenses over the horizon, not already in A_j, u_j, s_j or m_j.
- N_j: users sharing that service budget. The initial comparison holds N=1,000 fixed; this is not an adoption estimate.

The first numeric layer uses **A_j = (G_j − G_unchecked) × execution_price × ETH_EUR**, where G includes action and approval gas. It is an attributed incremental access cost, not a separately invoiced on-chain charge. The common unchecked-deposit cost belongs to u_j and is not subsidized in this initial experiment. Keep setup/operator budgets and unknown off-chain expenses separate. Add them to a monetary ledger only with an explicit payer, allocation period and non-overlap rule. An expanded pool requires an updated scope statement.

In the measured implementation the transaction sender pays the network. B2 assumes later reimbursement/accounting allocation; it does **not** implement a paymaster, change the sender, or measure reimbursement overhead. Any real payment mechanism has additional costs to assess.

The economic equations are:

```text
User payment:             U_j = u_j + alpha_j * A_j + f_j
Variable service expense: S_j = s_j + (1 - alpha_j) * A_j
Service balance:          Pi_j = N_j * (f_j + m_j - S_j) - F_j
Required net margin:      m_required,j = S_j - f_j + F_j / N_j   (N_j > 0)
Required extra benefit:   B_required = U_private - U_B0 + v * (t_private - t_B0)
```

t is **active user time** in hours and v its EUR/hour valuation. Server proof elapsed time is not a substitute. When time, prices or revenue lack evidence, keep their terms symbolic and report the measured component separately. Do not silently treat unknowns as zero. A signed benefit threshold may be negative; retain it and explain its conditional meaning. It is not an observed preference or demand curve.

The core fee rule is a common fixed fee f per user per 90 days, independent of alpha and frequency, held symbolic until a documented value/range is chosen. This is an experimental control, not a recommended tariff. For B0 and B1 the common fee cancels from their payment difference; for B2 it remains important to the service's coverage requirement. State f explicitly before a numerical profitability claim. Further fee rules require a separate named sensitivity case.

Avoid duplicate costs: do not add full G_j to both the unchecked part and its eligibility increment; do not add CPU/root gas already included in a provider invoice; and do not add a setup allocation both to F and per-user costs. User-to-service fees and reimbursements are transfers, not additional external resource costs. Do not add the ZK operator budget to a signed-only deployment merely because both were measured in a shared test registry.

## Work sequence and sweep

**ECON-03:** two-page note plus ledger/register. Start with 100 deposits over 90 days, K=1 service, N=1,000 users, four issuers, credential lifetime 90 days, authorization TTL 30 days, daily additions, weekly unrelated revocations, batched updates and policy `security`. Explain the selected methods and authorization counts, identify cost bearers, and show the symbolic B0/B1/B2 budgets. List missing evidence that could change a conclusion. Alexander reviews the boundary and inputs before the full economic run.

**ECON-04:** implement the approved economic ledger in a small reproducible program/notebook with a saved configuration. Consume the supplied frequency tables; there is no need to rerun contracts. Verify two hand-worked examples and allocation endpoints, transfer conservation, units, fixed-cost allocation and undefined N=0 ratios. The changing-alpha/offsetting-fee invariance is an accounting control, not a research discovery. AI-assisted checks do not replace the recorded human review of a central result.

**ECON-05:** use the [15-case plan](data/economic_sweep_plan.csv): deposits n=1,10,100 and alpha=0,0.25,0.5,0.75,1. Reuse the same signed B0 for each alpha at a given n. Report user payments, service subsidy/expense, required margin and required extra benefit; separate known components from unresolved terms. Use the two archived fee-price scenarios as monetary sensitivity, not two new physical experiments or quarterly-bill percentiles. Deliver machine-readable results, configuration, and 2–3 plots/tables answering specific questions.

Frequency traces start with a **new user's first access at day 0**, with subsequent accesses evenly spaced through the 90-day horizon. n=1 is one initial access, not a returning-user or randomly timed rare-user model. Returning credentials and residual validity require a separate trace and are not supplied by merely removing the issuance invoice.

Only after the core result, choose one extension: K=1 versus 5; lifetime 30 versus 90 days at n=100; the fixed-count phase table; or minute-scale revocation bursts. Do not run the full Cartesian product. The monthly aligned case and delay duplicates are controls, not independent findings. Revocation exposure duration is not monetary expected loss without incident/consequence evidence. Population, fee and cost sensitivity can be added when a sourced range or specific threshold question justifies it.

## Autonomy and technical requests

Nataliya owns the economic model, input-source audit and interpretation. She may complete literature/price research, symbolic analysis and documented sensitivity ranges without waiting for every unknown. Record unconfirmed assumptions as assumptions, with units and their effect on the conclusion.

For ZKP/privacy/device/L2 work, ask Alexander on the active ECON card: **which economic question is blocked, what event or property is missing, which unit/range is needed, and what conclusion depends on it**. Alexander validates or extends the technical inputs. Do not expand cryptographic implementation or legal-compliance claims as an economics task. Collect the first result on ECON-03; use ECON-04/05 sequentially after review.
