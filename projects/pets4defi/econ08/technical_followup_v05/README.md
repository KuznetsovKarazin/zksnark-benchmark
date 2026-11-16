# ECON 08 technical follow up v0.5

## Status checked 16 November 2026

Nataliya's Economic Addendum v0.2.1 (dated 15 November, returned 16 November) completes the requested economic checkpoint ahead of the soft 23 November target. Its ten manifest entries, verifier, K05/K06 split and all six archived daily SELF/PM operating cash cases pass internal review. A separate aggregation from the archived event inputs reproduces the cash targets and expenses. The original economic files and both source archives are preserved.

The next action belongs to Oleksandr: decide whether a precise additional scientific claim warrants a bounded extension. The original full-lifecycle G0a hypothesis has not passed, and the operating pooling inequality alone is not a new contribution. A32 and the broad campaign remain deferred. No further calculation or manuscript assignment is currently pending from Nataliya. The historical assignment below records what she has now completed.

The technical evidence is pinned at commit `333566637e2c67df2edfa2808903fc6beda8dfda`: CI, ECON-08 archived evidence and PETs4DeFi v2 all passed. This status clarification changes documentation only; the data, code, handoff ZIP and original measurements are unchanged. PR #3 remains draft and unmerged.

### Account definition and bounded economic interpretation

In `model_effects.csv` and `MODEL_SUMMARY.csv`, the reported delta K is **PM pool_K with weekly updates minus PM pool_K without updates**. It is neither the SELF change nor the within-scenario pooling gap. The underlying `model_grid.csv` separately reports `SELF_sum_K`. Calculate its weekly-minus-no-update difference using the same scenario, stage and refill key. The within-scenario pooling gap is `SELF_sum_K - pool_K`.

Checking all 5,760 median-grid rows confirms zero full-lifecycle changes for both accounts in all 360 ZK pairs at each daily and weekly refill policy. Daily continuing-service sign counts are:

| Mechanism | PM positive / zero / negative | SELF positive / zero / negative |
|---|---:|---:|
| B1 | 44 / 74 / 2 | 56 / 60 / 4 |
| B2 | 0 / 40 / 80 | 45 / 56 / 19 |
| B4 | 0 / 40 / 80 | 41 / 58 / 21 |

Each row covers 120 deterministic paired settings, not a probability estimate or new EVM measurements. The archived B2/B4 pattern (higher SELF targets but lower PM target) is therefore not universal for SELF. Published low/median/high coefficient sign checks concern the PM delta; this review has not extended that check to SELF.

For the archived B2 weekly operating case, the 441,106-gas pooling gap releases EUR 0.1247627276 of retained cash at historical q0. With an illustrative common annual capital rate r, an 89/365-year holding period and 392 operating accesses, the conditional PM-only overhead ceiling is `441106 * r * (89/365) / 392 = 274.3810036 * r` gas per access. At r = 10%, the total financing value is about EUR 0.00304216 and the ceiling is 27.4381 gas/access. This is an optimistic conditional ceiling, not measured AA overhead, observed financing rates or commercial viability. A common L1 gas-price multiplier scales the capital value and the gas charge equally; it does not improve this ratio. Fixed costs, changed prefunding requirements, different financing rates and fee/refill risks need separate treatment.

15 November 2026. The first economic checkpoint is complete. This addendum supplies the missing common-cost calibration, an independent event replay and bounded timing controls. Accepted ECON-07 and Nataliya's v0.2.4 submission remain unchanged.

## Decision after the bounded check

The original full-lifecycle hypothesis has not passed G0a. In all 360 ZK weekly/no-update pairs (120 for each B) at each of the daily and weekly refill policies, modeled full-lifecycle holder targets are identical when a common gas coefficient is used. The signed controls also have zero effect. The archived phase controls retain only small receipt-byte differences. Startup remains dominant in this tested grid.

A **separate startup funding policy** produces a different operating question. Startup expenses before lifecycle day 1 are paid from a dedicated startup budget; a new operating balance funds the remaining service on the original refill calendar. This can expose positive or negative operating-liquidity effects and pooling savings. It is a policy extension, not a replacement for the primary negative result. These patterns are candidates for economic interpretation; this result alone does not justify a broad A32 campaign.

## How the studies fit

PUB-01 explains reauthorizations and their gas costs. ECON-07 identifies lifecycle expenses, payments and funds. ECON-08 connects those events to the timing of available cash. We now have evidence that a larger 90-day expense need not require a larger operating reserve: revocations can shift otherwise synchronized TTL renewals into separate funding intervals. Conversely, B1 can concentrate renewals. This is a conditional timing result, not a universal benefit or disadvantage of revocation.

## Completed technical work

- Independent Python next-renewal recurrence: exact event, rejection reason, access time and cached expiry agreement for all 8,832 ordinary accesses in all 54 archived scenarios. This is a separate implementation, not an independent human replication.
- New unchecked calibration: three B=1/2/4 families, 1,200 successful deposits, 12 approvals, 12 rejected wrong-nonce static checks; 1,238 retained signed transactions verified. Same four holders, 100 deposits each, amount, nonzero gate balances, compiler settings and hardfork. No new ZK or paymaster execution.
- 72 archived refill-clock cases, each reported for full lifecycle and continuing service. Actor balances remain separate.
- 960 modeled workloads: four mechanisms, two access patterns, four common access phases, three TTLs, five grace values, and update/control pairs. The median grid contains 5,760 rows across three refill policies and two stages. Low/median/high observed event-gas coefficient scenarios retain the sign of every paired target effect; this is not an arbitrary independent-parameter confidence bound.
- Nine boundary/conservation tests cover expiry, publication ties, earliest invalidation, phase/stage accounting, no-refill and noncoincident pooling maxima.

## K05 and K06 are now supplied

For N16/A4/HIGH, the unchecked access subtotal is 22,040,752 gas for 400 deposits. Add the **original eligibility trace's actual approval gas** (185,852) to obtain K05 = 22,226,604 gas for the four-holder cohort. This avoids assigning a 12-gas deployment-address encoding difference in the B4 calibration to ZK eligibility.

K06 is the archived holder total minus that common baseline. For B2, K06 is 13,494,056 gas with weekly updates and 8,872,428 gas without updates. K05 + K06 exactly equals 35,720,660 and 31,099,032 gas respectively. At historical q0 these are K05 EUR 6.286588, K06 EUR 3.816668 / 2.509484, for four holders over 90 days.

These are attributed increments against a matched unchecked service, not an opcode-by-opcode decomposition. Operator deployment and issuer publications stay outside K05/K06. SELF and PM change the assigned payer, not these underlying quantities. Approval enables token transfer and is not ZK authorization. Full transaction gas must never be added again.

## Fixed continuing-service comparison

The table uses archived gas, daily refills, the original calendar and the day-1 startup boundary. All gas quantities cover four holders. They are actual-debit floors, not admission-safe reserves.

| B | Operating pool K with no updates | Operating pool K with weekly updates | Difference | SELF sum K with weekly updates | Pooling reduction |
|---|---:|---:|---:|---:|---:|
| 1 | 1,411,784 | 1,693,460 | +281,676 | 1,693,460 | 0 |
| 2 | 1,411,844 | 1,117,194 | −294,650 | 1,558,300 | 441,106 |
| 4 | 1,411,832 | 829,043 | −582,789 | 1,490,666 | 661,623 |

For B2, pooling reduces the sum of separate operating targets by about 28.3%, but only EUR 0.124763 at q0 for four holders. This does not reduce gas expense or erase startup costs. Report both relative and absolute scale. The issuer-labelled peaks remain role-account assignments; the original fixture does not establish separate legal treasuries.

## Exact recurrence and cash calculation

Let a_i be successive eligible-holder access times, u the first relevant publication strictly after the last authorization a_j, and L the TTL. The next authorization index is the first i > j satisfying a_i >= min(a_j+L, u+delta, credential expiry). If there is no such i in the horizon, there is no further authorization. A publication at a_j precedes that authorization and is already included in its current state. Later updates do not extend the first invalidation deadline. Signed credentials in these unrelated-revocation cases renew only on TTL expiry.

With constant event gas prices, each window debit is the sum of approval, first-authorization, renewal and cache-hit debits. K is the maximum of these window sums. For each reset-to-target account, G = K + subsequent top-ups and G − expense = ending cash. No refill implies K = cumulative expense. Pool K cannot exceed the sum of separate holder K values; equality depends on peak alignment. No Poisson expectation or population scaling has been established in this deterministic study.

## Historical assignment — completed 16 November 2026

Please return **one short addendum, about 1–2 pages**, using the small tables in the v0.5 handoff. A soft target is **23 November**, adjustable together, so we can discuss it before the 25 November meeting.

1. Replace the previously unknown worked-case K05/K06 split with the supplied crosswalk and retain the original totals. Preserve accepted ECON-07 and the submitted v0.2.4 files; save a new revision.
2. Explain the full-lifecycle result and the separate continuing-service result. State who supplies startup capital, operating balances and later refills. Explain why a lower pool target is not a lower expense or necessarily lower total treasury funding.
3. Assess the economic meaning at q0 and at the supplied logarithmic price multiples. Distinguish an illustrative funding limit from an observed budget or willingness to pay. Flag whether the operating-policy extension is substantive enough to pursue as a separate contribution.
4. Use the documented OP projection as a conditional fee scenario; keep true paymaster validation/bundling overhead, refill delay/fees and off-chain KYC/issuance prices explicit. Do not choose new cryptographic rules or run software.

All source code, the full grid, raw calibration and RPC evidence are **for information only**. Oleksandr owns technical validity, scope decisions, any A32 measurement and claims of novelty. No full manuscript or new literature campaign is requested at this checkpoint.


## Historical OP fee scenario

The B2 projection includes execution, L1 data and the queried operator component at OP block 158458797 (20 October 2026), with the archived execution-price proxy of 6,661 wei/gas. The full measured service costs EUR 0.012633005 with weekly updates and EUR 0.011459508 without updates for the four-holder workload. The continuing-service daily pool targets are EUR 0.000247057 and EUR 0.000298652. The queried operator fee is zero at this pinned block. These are conditional direct-transaction projections, not OP execution or ERC-4337 measurements; see [the fee note](handoff/OP_FEE_NOTE.txt). Original receipts, all 397 RPC records and an offline verifier support all 848 quotes. No price volatility or fee-overhead guarantee is implied.

## Reproduce and inspect

From `examples/pets4defi_access_v2`, after `npm ci --ignore-scripts`:

```sh
node scripts/econ08/verify_followup.mjs
node scripts/econ08/verify_op_projection.mjs
python3 -m unittest discover -s ../../projects/pets4defi/econ08/technical_followup_v05 -p 'test_followup.py' -v
python3 ../../projects/pets4defi/econ08/technical_followup_v05/analyze.py
python3 ../../projects/pets4defi/econ08/technical_followup_v05/summarize_op.py
```

All these checks use retained evidence and require no network. To acquire fresh calibration into a new directory, run `node scripts/econ08/unchecked_calibration.mjs /absolute/new/output`. To repeat the historical read-only OP query, run `node scripts/econ08/quote_op_fees.mjs /absolute/new/output`; this requires archive RPC access. The packet generator additionally requires python-docx and matplotlib. Original v0.4 evidence and Nataliya's v0.2.4 files are not overwritten.

The analysis plan was saved in a local commit before the new calculations; it is not an external preregistration and already knew the prior startup-dominance result. Read [the declared scope](ANALYSIS_PLAN.md) before interpreting the grid. Raw retained data verify internal consistency; independent external replication remains open.
