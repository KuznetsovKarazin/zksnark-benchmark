Research protocol for private DeFi eligibility

ECON 07 and ECON 08  |  Version 0.2  |  13 November 2026

Oleksandr Kuznetsov and Nataliya Kolyada

We will combine the lifecycle accounting of ECON-07 with the technical evidence of ECON-08 in one study. This protocol defines the research question, the new contribution to test, and the division of work. The accepted ECON-07 results and the existing measurements remain identifiable as earlier evidence.


## Research objective and contribution

Identify the lowest lifecycle resource cost among designs that meet stated privacy and revocation requirements and admit a payment rule covering costs, respecting participant budget constraints, and maintaining sufficient cash and reserve throughout the workload. Report an empty feasible set when no such rule exists. This is the research objective; the optimum and feasibility boundaries have not yet been established.

PUB-01 already develops expected authorisation counts, population-dependent revocation rates, issuer partitioning, TTL sensitivity and cost sharing [1]. The candidate contribution here is the joint boundary of technical and financial feasibility, including active participation, revocation grace and uncertain prices. Reproducing those earlier models or figures alone does not establish a new contribution.


## Design and workload

Design x | Issuer groups B, revocation grace δ, and authorisation TTL.

Population | N issued credentials; active fraction a; A = aN active holders.

Horizon and revocations | H = 90 days; r expected revocations per credential per horizon.

Prices and requirements | q is gas price; specify the currency conversion, minimum issuer set, and maximum accepted revocation delay separately.

For four issuers, B = 1, 2 or 4 leaves a possible issuer set of 4, 2 or 1, conditional on public metadata. Wallet and application-level linkage remain. The signed control exposes the issuer and credential identifier; it has a different privacy profile.

In the native design, δ is grace after immediate authoritative publication. It may combine the effects of several updates into one later authorisation; it does not batch publications. Later updates cannot extend the first invalidation deadline. The current cap is one day. Testing 3, 7 or 14 days requires a contract change and boundary checks. Issuer reporting delay is outside the current publication-based clock.


## Accounting and feasibility

Use one versioned event ledger for all technical and economic outputs. Count shared deployment once, separate recurring costs, and distinguish initial KYC from an already-issued cohort. Internal transfers change the payer, not total resource use. Price sources, unknown costs, hypothetical budget caps and sponsor commitments must remain explicit. Budget feasibility is not measured willingness to pay or incentive compatibility [2].


## Evidence and validation

The 32 pilot and 22 cohort scenarios are existing evidence. Cohort N = 16, 128 and 512 runs observe four active wallets; they do not measure a population of N active users. Preserve raw receipts and source versions. This update introduces no new experimental results.

First, reconstruct each known event schedule with an independent deterministic model and require exact agreement in event counts on all 54 traces. Define full authorisations, revocation-triggered authorisations and extra authorisations relative to a matched no-update control separately. Then test stochastic expectations against independent simulations, confidence intervals and boundary cases; an expectation need not match each individual trace within one event.


## Bounded extension of the experiment

Use balanced independent revocations as the initial model. Its expected group count is rN/B over 90 days; the corresponding daily rate is rN/(90B). State whether revoked credentials leave the population or are replaced, and handle a holder’s own revocation explicitly. Add unequal activity or correlated incidents only as specified sensitivity cases.

Separate issued population from active workload. Plan EVM checks with 32 and 64 active holders, paired no-update controls, and the same event schedules across designs. Extend δ only after correctness tests. Model larger populations separately: the present four depth-10 trees hold at most 4096 credentials, so projections to 10⁴–10⁵ require an explicit capacity and cost assumption.

Vary gas prices over a logarithmic range and retain the original reference price. Add one dated L2 scenario including execution, L1 data and operator fees [3]. Keep W3C Status List in a qualitative guarantee comparison [4]; PRC and CRSet remain related work. Local lookup milliseconds are not a full alternative DeFi cost.


## Responsibilities and first deliverable

Oleksandr defines the observer model, admissible privacy and freshness conditions, event semantics, technical model, code and validation evidence. Nataliya maps K01–K16 to trace events, records sourced or symbolic off-chain prices, and derives payment, tariff and reserve feasibility. Her first deliverable is the event mapping, a price and uncertainty table, and the financial constraints with missing technical inputs identified. No new cryptographic implementation or deadline is assigned to her.


## Planned results and figures

1. Authorisation burden as grace and active workload vary, with model predictions and EVM checks. 2. Lifecycle cost and partition break-even boundaries, separating shared and per-holder costs. 3. Technically and financially feasible designs under stated privacy and revocation requirements. 4. Tariff intervals and reserve requirements on the same event inputs. Each figure must answer a new question relative to PUB-01; a missing or empty feasible region is a valid result.


## Sources and working records

[1] PUB-01 manuscript, 7 November 2026, §§3.5, 4.4 and 5.

[Manuscript record](https://trello.com/c/tTUolaRK)

[2] ECON-07 Methods and Results v0.1.

[Accepted synthesis](https://docs.google.com/document/d/1hNPRNmUMegg88hn6mpCLO6pxj67zb48C7-m8wdO5FcE/edit)

[3] OP Mainnet transaction fee components.

[Official specification](https://docs.optimism.io/op-stack/transactions/fees)

[4] W3C Bitstring Status List v1.0, 15 May 2025.

[Recommendation](https://www.w3.org/TR/2025/REC-vc-bitstring-status-list-20250515/)

Tasks, questions and versioned handoff.

[ECON-08 card](https://trello.com/c/8i08gLxj)
