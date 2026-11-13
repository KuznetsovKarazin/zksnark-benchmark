# Economic checkpoint for private eligibility funding

ECON-07 + ECON-08, v0.3, 13 November 2026. Nataliya Kolyada and Oleksandr Kuznetsov.

Please prepare a short economic note of about **2–3 pages**, the three starter templates and one worked example. A first pass with clear missing inputs is enough. **Soft target: 30 November 2026; we can adjust it together.** This replaces the v0.2 first-checkpoint assignment.

The question is what holder funding, sponsor support and initial liquidity each technically admissible design requires. Treat budgets as outputs conditional on payment rules. We do not assume that funding constraints necessarily change the cheapest design.

## What to read and return

Read the [two-page protocol](ECON07_08_Research_Protocol_v0_3.docx), then the instructions below. Fill the ten-column templates as far as the evidence permits. Blank means unknown, never zero. CSV files use UTF-8 with commas. No software installation is required.

| Required file | First return |
|---|---|
| [ledger_mapping_TEMPLATE.csv](ledger_mapping_TEMPLATE.csv) | Accepted K01–K16 mapped to events, units, actors and evidence |
| [price_assumptions_TEMPLATE.csv](price_assumptions_TEMPLATE.csv) | Dated price evidence, explicit scenarios and missing prices |
| [feasibility_TEMPLATE.csv](feasibility_TEMPLATE.csv) | Funding and liquidity conditions for one worked case |

The [implementation plan](optional/IMPLEMENTATION_PLAN_V03.md) is **for information only**. It is not required reading or a task list for you. Optional [validation](optional/reference/VALIDATION.md), [pilot results](optional/reference/RESULTS.md) and [cohort results](optional/reference/COHORT.md) are included in this ZIP. These reading links work after extraction without GitHub access. The full technical code and rerun are Oleksandr's responsibility.

## 1 Map the accepted costs

Use the [accepted ECON-07 synthesis](https://docs.google.com/document/d/1hNPRNmUMegg88hn6mpCLO6pxj67zb48C7-m8wdO5FcE/edit). Copy K01–K16 and their definitions exactly. Duplicate a row if one definition maps to several events or actors. Record quantity and unit, resource-bearing actor, initial payer and final bearer, and the exact evidence field or source. Keep real costs, transfers, reserve principal and financing costs distinct.

The original [pilot summary](pilot_summary.csv) has one observed holder. The [cohort summary](cohort_summary.csv) has four active holders, even when N=16/128/512 credentials are issued. Shared deployment occurs once; initial root publication is not the cost of issuing a credential. Fields `holder_cohort`, `operator_setup`, `initial_publication`, `status_publication`, `authorizations` and `updates` have the meanings recorded in the cohort note. Ask Oleksandr for event splits if aggregate gas is insufficient; do not apportion it without evidence.

## 2 Record prices without inventing budgets

For a price, give its currency/unit, applicable service/tier, tax treatment, source and date. Keep missing off-chain prices unknown or symbolic. KYC and credential issuance are distinct unless a provider explicitly bundles them. A provider's price is procurement evidence, not willingness to pay.

The template includes the historical ECON-07 reference q0=0.130658648 gwei/gas and e0=2164.73 EUR/ETH. These are not current quotes. Convert with `EUR = gas × q_gwei × 10^-9 × EUR_per_ETH`. Keep gas-price and exchange-rate sensitivity separate. Oleksandr supplies the full L2 fee inputs; no arbitrary L1 discount is needed from you.

The earlier EUR0.60/EUR4 budgets remain historical scenarios. Instead calculate required holder funding as a function of sponsor support and payment rules. Prior KYC outside the 90-day horizon and new issuance within it are different cost boundaries.

## 3 Work one funding example

Start with N=16 issued credentials, A=4 active holders, HIGH, weekly, δ=0, over 90 days. These are original measured quantities:

| Mechanism | Full authorizations, all 4 | Holder gas, all 4 | Shared gas | Total gas |
|---|---:|---:|---:|---:|
| B1 | 52 | 42,613,620 | 13,817,033 | 56,430,653 |
| B2 | 28 | 35,720,660 | 16,592,944 | 52,313,604 |
| B4 | 16 | 32,274,048 | 24,791,056 | 57,065,104 |
| Signed | 12 | 32,925,732 | 13,328,181 | 46,253,913 |

Shared gas sums deployment, initial publication and later publications. The signed mechanism has different privacy; it is a diagnostic reference. Without updates, all four mechanisms have 12 full authorizations in total. For B2, weekly adds 16 authorizations overall, or 4 per holder.

Begin with an unrestricted-pooling benchmark: if total resource cost is C, sponsor funding is capped at s and A holders may fund the remaining costs without timing restrictions, the uniform minimum holder budget is `max(0,(C−s)/A)`. Under these assumptions, if any design is fundable then the cheapest admissible one is fundable. Raising gas price does not overturn that fact.

Then state a realistic payment rule before recalculating. For example, if holders fund only their own transactions and sponsor support covers shared costs, report both the required sponsor amount and required holder budget. This example is a scenario, not observed project policy. Explain who pays which bill and when, what transfers are permitted, and any shortfall. A minimum liquidity amount must name its actor and collection/refill schedule. Do not tune constraints solely to force a change of preferred design.

In `feasibility_TEMPLATE.csv`, `min_holder_budget_EUR_90d` is per active holder; `min_initial_liquidity_EUR` is for the actor named in that row. `support_and_payment_timing` records the sponsor amount/rule and when money is available. `calculation_or_source` points to the formula or note. Keep `not_evaluated` where inputs are missing. Add rows for other actors/payment rules as needed.

## Boundary and next step

Oleksandr first runs the early go/no-go check, then owns technical validation and any new measurements. The present package does not report new EVM runs. Longer δ=3/7/14-day cases are model-only; the single planned new EVM workload uses A=32. Own-revocation and reissuance economics are deferred, while existing security tests remain.

Your return should identify the accounting boundary, provide the worked funding example and price evidence, and list the few missing technical inputs that could change the result. You do not need to rebuild all accepted ECON-07 calculations, derive the cryptographic model or read the optional technical plan. Post the note and templates on [ECON-08](https://trello.com/c/8i08gLxj).
