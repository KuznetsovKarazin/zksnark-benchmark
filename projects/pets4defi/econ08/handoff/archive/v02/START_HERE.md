# ECON-07 + ECON-08: economic checkpoint v0.2

Nataliya Kolyada and Oleksandr Kuznetsov · PETs4DeFi · 13 November 2026

Please prepare a **2–3 page economic note and three completed CSV templates**. A first pass with explicit missing inputs is sufficient. The question is which technically admissible configuration can be funded, by whom, and under what prices and budget assumptions. Read [ECON07_08_Research_Protocol_v0_2.docx](ECON07_08_Research_Protocol_v0_2.docx). This assignment replaces the v0.1 design-note assignment.

Oleksandr owns the privacy definitions, authorization model, correctness checks and further experiments. Your part is economic event mapping, unit prices, payment allocation and financial feasibility. A complete manuscript, cryptographic comparison or full economic model is not required now.

## Files and evidence

| File | Use |
|---|---|
| `ECON07_08_Research_Protocol_v0_2.docx` / `.md` | Two-page research protocol and its text copy |
| `IMPLEMENTATION_PLAN_V02.md` | Staged technical/economic work and acceptance gates |
| `pilot_summary.csv` | Original 32-scenario pilot summary; one observed holder |
| `cohort_summary.csv` | Original 22-scenario cohort summary; four observed holders |
| `ledger_mapping_TEMPLATE.csv` | K01–K16 definitions, events, actors and evidence |
| `price_assumptions_TEMPLATE.csv` | Historical reference prices, new sources and uncertainty |
| `feasibility_TEMPLATE.csv` | Four measured example designs; blank financial fields |
| `SHA256SUMS` | Checksums of active instructions, protocol and CSVs |

No software setup is required. CSV files use UTF-8 and comma delimiters. Blank means **not yet supplied**, never zero. Duplicate a K row when one accepted definition maps to several events/actors, and explain the allocation. Add rows without changing original measured inputs.

The existing evidence has 8,832 ordinary accesses; all 512 saved proofs and 10,627 signed transaction records passed revalidation on 13 November. This was an audit, not new population/extended-delay/L2 measurement. The complete repository contains [validation](../VALIDATION.md), [pilot results](../RESULTS.md) and [cohort results](../COHORT.md); these three links require the repository. The standalone ZIP includes all ten files listed above, including [the implementation plan](IMPLEMENTATION_PLAN_V02.md). Repository-relative evidence links inside that plan require the complete technical package. Historical v0.1 and W3C timing files are excluded from the active packet.

## 1. Map K01–K16 to events

Use the [accepted ECON-07 synthesis](https://docs.google.com/document/d/1hNPRNmUMegg88hn6mpCLO6pxj67zb48C7-m8wdO5FcE/edit). Copy each accepted K identifier and definition exactly, including its boundary. The template contains K01–K16 with blank definitions/mappings: it does not assign new meanings.

Record the event, resource-bearing actor, paying actor, quantity/unit, scenario ID and source field. Distinguish resource cost, internal transfer, reserve stock and cost of capital. Keep setup, credential issuance, initial root publication, later status publication, full authorization, cache hits and off-chain services separate. Mark unmeasured items as missing, not zero.

| Event/resource | Cohort field | Interpretation |
|---|---|---|
| Approvals and successful accesses | `holder_cohort` | Gas for four wallets, including full authorizations and hits |
| Shared deployment | `operator_setup` | Once per run, not once per holder |
| Initial issuer roots | `initial_publication` | Publication gas, distinct from credential issuance |
| Later publications | `updates`, `status_publication` | 12 in weekly cases; zero in no-update controls |
| Full authorizations | `authorizations` | Total includes initial and TTL renewals |
| KYC, issuance, hosting, witness delivery | Accepted ledger and requested technical inputs | Unmeasured; not free |

Detailed evidence is in `examples/pets4defi_access_v2/results/econ08_native_pilot/cost_ledger.csv` and cohort `results/econ08_cohort/runs/` ledgers. Ask Oleksandr for event splits rather than apportioning aggregate gas without evidence. Reimbursement changes who pays; it does not create a second gas resource cost.

## 2. Prices and uncertainty

For each price give low/reference/high where justified, currency/unit, applicable tier/volume, tax treatment, source URL and quotation/access date. Label quoted prices, historical references, scenarios and unknowns. Public KYC provider prices support procurement costs, **not willingness to pay**. Treat KYC and credential issuance as separate services unless a source bundles them.

The former EUR 0.60/4 budget caps and EUR 0.01–0.04 operating assumptions are hypotheses, not sourced prices or observed demand. Keep caps separate from prices and show thresholds where conclusions change. State whether prior KYC is outside the horizon or new KYC inside it. Common costs may cancel between mechanisms while remaining relevant for funding.

The template includes only historical ECON-07 §2.1 reference inputs: q0=0.130658648 gwei/gas and e0=2,164.73 EUR/ETH. They are not current quotes. Use `EUR = gas × q_gwei × 10^-9 × EUR_per_ETH`. Explore absolute gas prices logarithmically, including 1/10/100 gwei, with exchange-rate uncertainty separate. Any multiplier must name its reference.

For the planned L2 example Oleksandr supplies execution, L1 data and applicable operator fee inputs under a documented network/version. An arbitrary discount on L1 gas is not that model.

## 3. Worked example and feasible payments

Start with N=16, A=4, HIGH, weekly and δ=0. N is issued credentials; A is observed active wallets. The horizon is 90 days. Seeded feasibility rows contain measured quantities, not evaluated viability.

| Mechanism | Authorizations, all 4 | Per wallet | Measured total gas |
|---|---:|---:|---:|
| B=1 | 52 | 13 | 56,430,653 |
| B=2 | 28 | 7 | 52,313,604 |
| B=4 | 16 | 4 | 57,065,104 |
| Signed | 12 | 3 | 46,253,913 |

B1 minus signed is 10,176,740 gas across four wallets. At the historical prices this equals EUR 2.878396 total or **EUR 0.719599 per active wallet per 90 days**. Divide by 4, not by 16. State shared-setup allocation. The mechanisms have different privacy guarantees. With no updates the corresponding difference is negative; higher gas prices can materially increase it. “Privacy is cheap” and “KYC dominates” remain conditional hypotheses.

For each actor show resource cost, payments made/received, coverage and minimum balance over time. Define fee intervals using explicit budget caps and obligations; mark an empty interval infeasible. Keep reserve stock separate from its financing cost. Missing prices/quantities/constraints make the affected result unavailable.

The four-holder ranking is not a universal B optimum. Linear replication of this workload projects a B4/B2 crossover at A≈9.5144 (10 holders, or 12 under exact four-issuer balance). It awaits active-holder measurements and is not itself measured.

## Template fields and first return

- **Ledger:** `accepted_definition` and `accepted_source_locator` come from ECON-07. `resource_actor` consumes the resource; `payer_actor` funds it. Quantity/unit, scenario, evidence file/field, accounting type and allocation make each mapping auditable. Leave unresolved mappings explicit.
- **Prices:** keep native currency/unit and distinguish evidence from scenarios using `source_type`. Budget-cap rows use `budget_constraint`, not `procurement_price`. `status` and `open_input` identify gaps.
- **Feasibility:** example counts/gas are prefilled; monetary fields are blank. Use actor-specific rows or reference an actor allocation table. State payments, coverage, reserve and fee bounds. An aggregate cost alone cannot establish every actor's viability. Keep `not_evaluated` until the required inputs exist.

Return a short note containing (1) the economic boundary and unresolved mappings, (2) the worked example and price evidence/scenarios, and (3) conditional payment/coverage/reserve bounds and missing technical inputs, together with the three populated templates, on the [ECON-08 card](https://trello.com/c/8i08gLxj). No new deadline is imposed.
