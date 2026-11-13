Research protocol for liquidity in private DeFi access

ECON 07 and ECON 08  |  Version 0.4  |  13 November 2026

Oleksandr Kuznetsov and Nataliya Kolyada

PUB-01 explains revocation costs, ECON-07 defines actors and payment rules, and ECON-08 supplies timed events. We now ask whether revocation-driven payments exhaust funds before the next refill even when total service cost is affordable, and define the first economic test.


## Research question and candidate contribution

For required issuer privacy and revocation freshness, how do grouping, grace, access timing and refill policy affect minimum prefunding? The candidate contribution is a quantified liquidity spillover: a group update may concentrate later holder payments and change funding requirements beyond what total or average cost explains.

Renewals occur at subsequent accesses, not at publication. Their concentration depends on activity, TTL, grace, existing authorisations and refill timing. We will separate additional resource use from payment timing and test whether either changes an admissible design or funding requirement.

PUB-01 already covers Poisson updates, population, TTL, partitions and cost sharing [1]. Unrestricted, costless funding without timing constraints preserves cost ordering; this and budget arithmetic are controls. A new contribution requires a demonstrated effect specific to these access and revocation mechanisms.


## Two fixed financing scenarios

SELF: holders initially pay their own transaction gas; issuers and the operator pay shared transactions. This defines the initial payer and permits separately recorded reimbursements.

PM: a prepaid paymaster funds holder approvals and access transactions, including full authorisations and cache hits. Shared issuer and operator transactions stay outside its account. The primary scenario restores a target balance every 24 hours; the target is an output. Initial funding occurs at the common fixture origin, before setup. Refills occur on that grid before coincident payments. Apply the same grid to SELF wallets and separate shared accounts. Weekly refill and no refill are sensitivity scenarios, not observed policies.

Assume instantaneous, fee-free refills and no customer collections or reimbursements in the baseline. Keep treasury obligations separate from account balance targets. PM differs from v0.3 operator_only_sponsor, which funded shared costs. Record any later collections, reimbursements and actor balances separately. Nataliya will use these fixed rules.


## Early decision gate

G0a follows the accounting boundary in G0 and precedes new EVM measurements. Compare SELF and PM on existing traces with matched no-update controls; vary payment/refill phase and separate setup from ongoing access costs. Check whether peak shortfalls survive reasonable timing and price changes.

G0a remains open. A paymaster standard establishes a possible mechanism, not novelty or practical importance. Proceed only if trace analysis identifies a distinct, useful result; otherwise revise the claim before extending the campaign. Report conditional thresholds and required budgets rather than presumed user budgets.


## Design and accounting boundary

Use a 90-day horizon. B counts issuer groups, δ is post-publication grace, and TTL is authorisation lifetime. N is issued credentials; A is active holders. Retain explicit privacy constraints and the different guarantee of the signed control. Count each resource once. Transfers change the payer; prefunding is a stock, with any financing cost recorded separately [2].


## Liquidity measure and implementation limits

For a fixed funding schedule, minimum cash is the largest positive gap between cumulative covered payments and cumulative available receipts over the event trace. For refill-to-target PM, compute the required target across refill intervals, including startup. With no refill or receipts and nonnegative charges, the requirement reduces to total cost. Use this case as a control.

Existing traces contain direct transactions. Their measured costs supply the debits for a serial cash-flow model. The resulting spending floor is not a measured paymaster deposit. Account-abstraction validation, bundling and paymaster overhead remain unmeasured. A real paymaster also needs validation prefunding from gas limits and fee bounds [3], potentially above actual expenditure. Keep it separate until calibrated; the simulated balance does not guarantee admission of bundled operations.


## Evidence and focused experiment

Preserve the 32 pilot and 22 cohort scenarios. The cohort observes four wallets even when N is 16, 128 or 512. Reconstruct all 54 schedules independently and require exact agreement in counts and boundary decisions. Distinguish full authorisations, revocation-triggered renewals and excess renewals over a matched control. Begin with deterministic liquidity traces; estimate stochastic tails only if G0a finds a material effect.

Use unrelated revocations while the focal holder remains eligible. Link rates to the issued population with stated units. Own-revocation and reissuance economics are deferred; security checks for revoked credentials, expiry and emergency rejection remain required. δ does not batch publications, and later updates must not extend the first invalidation deadline.

Keep δ of 3, 7 and 14 days in the model only; the contract cap remains one day. Plan one A = 32 EVM workload configuration with matched mechanisms and no-update controls. A = 64, larger populations and contract changes are deferred. Current capacity is 4096 credentials. Add logarithmic gas-price scenarios and one documented L2 model including execution, L1 data and applicable operator fees [4].


## Economic checkpoint and responsibilities

Oleksandr defines technical semantics, the fixed financing rules, liquidity calculation and validation. Nataliya maps K01–K16 to the timed events and actors, sources prices, and records funding requirements and missing inputs under SELF and PM. Her first deliverable is a short note, simplified templates and one worked example. The implementation plan is for information only.

Use 30 November 2026 as an adjustable target for the first pass. Nataliya is not asked to choose the base rules, implement software or analyse cryptographic security. The former €0.60/€4 caps remain optional sensitivity assumptions, not measured willingness to pay.


## Outputs and limitations

Prioritise new figures showing payment timelines, required funding across refill policies, and sensitivity to grace, activity and phase. Distinguish measured transaction quantities, model projections and uncalibrated paymaster costs. Keep W3C Status List qualitative; PRC and CRSet remain related work. Synthetic workloads and unknown demand limit interpretation. No new EVM or paymaster implementation is claimed here.


## Sources and working records

[1] PUB-01, 7 November 2026.

[Manuscript record](https://trello.com/c/tTUolaRK)

[2] ECON-07 Methods and Results v0.1.

[Accepted synthesis](https://docs.google.com/document/d/1hNPRNmUMegg88hn6mpCLO6pxj67zb48C7-m8wdO5FcE/edit)

[3] ERC-4337 account abstraction.

[Specification](https://eips.ethereum.org/EIPS/eip-4337)

[4] OP Mainnet transaction fees.

[Official documentation](https://docs.optimism.io/op-stack/transactions/fees)

Current task and versioned handoff.

[ECON-08 card](https://trello.com/c/8i08gLxj)
