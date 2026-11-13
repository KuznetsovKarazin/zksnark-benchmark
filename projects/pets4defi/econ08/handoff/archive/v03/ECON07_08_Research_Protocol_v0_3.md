Research protocol for financing private DeFi eligibility

ECON 07 and ECON 08  |  Version 0.3  |  13 November 2026

Oleksandr Kuznetsov and Nataliya Kolyada

We will study which private access configurations use the least resources, what funding holders and sponsors require, and when payment restrictions change the feasible choice. ECON-07 supplies the accepted economic ledger; ECON-08 supplies technical traces. We will test the scientific case before extending the experiment.


## Research questions and potential contribution

PUB-01 already covers expected authorisation counts, Poisson updates, population effects, TTL, issuer partitioning and basic cost sharing [1]. These elements are our starting point. The new study must establish an additional result; relabelling earlier curves or figures is insufficient.

First, determine when minimising total resource cost also minimises required funding, and which restrictions on payment routes, sponsor commitments or collection times can break that equivalence. The unrestricted case is a necessary reference: if transfers are free and unrestricted, aggregate funds are the same across designs and timing imposes no constraint, a cheaper admissible design cannot be excluded while a more expensive one remains affordable.

Second, derive the minimum holder contribution and sponsor funding required by each design, together with the liquidity needed along the event timeline. Report these as conditional frontiers, with payment rules and available sponsor funds explicit. A holder budget alone is not meaningful if unlimited sponsorship can reduce it to zero.

Third, identify operating regions where the design choice or funding requirement changes with activity, grace, workload and prices. Test stability to uncertainty and whether shared group updates cause funding peaks that average cost conceals. These are candidate contributions; their importance and distinction from PUB-01 remain to be demonstrated.


## Early decision gate

Immediately after fixing the common accounting boundary in G0, run G0a on the existing gas quantities. Start with the unrestricted funding reference, then examine independently justified payment restrictions. Sweep gas prices, active population and sponsor capacity; calculate required budgets as outputs. Record whether a restriction excludes the cheapest admissible design while retaining another, makes every design infeasible, or changes only the required funding.

Increasing gas price alone cannot overturn the unrestricted result. A scenario constructed to produce a reversal does not establish practical relevance. Proceed to the larger study only if supported restrictions, a useful funding frontier or a substantive operating-regime result provides a distinct question. Otherwise revise the central claim before new EVM work. Do not infer an L1 threshold or absence of an L2 effect without the corresponding fee and payment model.


## Parameters and accounting

The design uses B issuer groups, grace δ and authorisation TTL. N counts issued credentials; A counts active holders. With four issuers, B = 1, 2 or 4 leaves potential issuer sets of 4, 2 or 1, conditional on public metadata. Wallet linkage remains. The signed reference has different privacy guarantees.

Use a 90-day horizon and a defined revocation process. Keep shared deployment, publications and holder costs separate. Use one event ledger for technical and economic outputs. Transfers redistribute payment; reserve stock is not an expense. Treat the former €0.60/€4 caps as optional sensitivity assumptions, not measured demand. Separate already-verified cohorts from new issuance [2].


## Evidence and validation

The existing evidence contains 32 pilot and 22 cohort scenarios. The cohort runs observe four active wallets even when N is 16, 128 or 512. Preserve the original traces. Independently reconstruct all 54 event schedules and require exact agreement in counts and boundary decisions. Distinguish full authorisations, revocation-triggered renewals and excess renewals over a matched no-update case. Validate stochastic expectations against simulation means and confidence intervals, not within one event of every random trace.


## Focused experimental scope

For fixed payment and refill schedules, calculate minimum prefunding as the largest positive cumulative payment shortfall over all event prefixes. This measures peak liquidity, separately from expected total cost. Start with deterministic traces; estimate tail risk under random schedules only if G0a shows a material effect.

Begin with unrelated revocations affecting an otherwise eligible focal holder. Link the group event rate to the issued population and state whether the input is an expected count or a probability. The first version excludes the economic extension for the holder’s own revocation and reissuance. Existing correctness checks for revoked credentials, expiry and emergency rejection remain required.

δ is grace after immediate publication; it does not batch publications. Later updates must not extend the first invalidation deadline. Keep 3, 7 and 14 days in the model only; the current contract cap remains one day. Add one EVM workload configuration with A = 32, matched mechanisms and no-update controls. Larger populations, A = 64 and contract changes are deferred. The present four depth-10 trees hold at most 4096 credentials.

Use logarithmic gas-price scenarios and one documented L2 fee model, including execution, L1 data and applicable operator fees [3]. Separate price effects from payment constraints. Compare W3C Status List qualitatively by guarantees; PRC and CRSet remain related work. Local lookup milliseconds are not comparable to full DeFi gas costs.


## Economic checkpoint and responsibilities

Oleksandr owns the technical semantics, guarantee comparison, early decision gate, model and validation. Nataliya maps K01–K16 to events, sources prices, and formulates minimum funding and liquidity requirements. Her first deliverable is a short note, the simplified templates, one worked case and unresolved inputs. The implementation plan is for information only; reading it is not required for this checkpoint.

Use 30 November 2026 as a soft target for a first pass, adjustable by agreement. Missing evidence should stay explicit. No software implementation or cryptographic analysis is assigned to Nataliya.


## Planned outputs and limits

Produce new figures for funding frontiers, active-population and grace regimes, admissible designs under payment restrictions, and liquidity or tariff bounds. Select the final figures after G0a. The unrestricted result is a reference, not sufficient novelty by itself. Model-only grace extensions, synthetic workloads, conditional prices and unmeasured demand limit interpretation. No new EVM measurement, market validation or publication outcome is claimed by this protocol.


## Sources and working records

[1] PUB-01, 7 November 2026, §§3.5, 4.4 and 5.

[Manuscript record](https://trello.com/c/tTUolaRK)

[2] ECON-07 Methods and Results v0.1.

[Accepted synthesis](https://docs.google.com/document/d/1hNPRNmUMegg88hn6mpCLO6pxj67zb48C7-m8wdO5FcE/edit)

[3] OP Mainnet transaction fee components.

[Official specification](https://docs.optimism.io/op-stack/transactions/fees)

Current instructions and versioned handoff.

[ECON-08 card](https://trello.com/c/8i08gLxj)
