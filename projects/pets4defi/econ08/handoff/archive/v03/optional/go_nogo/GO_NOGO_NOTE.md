# Early scientific gate for ECON-07 and ECON-08

13 November 2026. This note reports a new algebraic and numerical diagnostic using archived gas data. It reports no new EVM experiment, provider-price evidence, L2 fee result or observed financing arrangement.

## What the review gets right, and the additional structural issue

Move the scientific go/no-go gate immediately after G0. Do not spend the implementation campaign trying to obtain a preferred financial-design reversal. It is useful to compute minimum required budgets instead of treating EUR 0.60/4 as observed willingness to pay. However, a minimum holder budget is conditional on sponsor resources, permitted transfers, billing times and cost coverage. With unlimited sponsorship it can be zero by construction.

The main problem with the v0.2 central claim is stronger than small euro differences. Under unrestricted costless transfers, a financing constraint cannot exclude the least-cost design while retaining a more expensive design with the same aggregate resources. A gas-price sweep cannot repair this structural fact.

**No-reversal proposition.** Let X be a fixed set of technically admissible designs. Design x incurs nonnegative resource cost C(x). All actors together can supply the same aggregate funding F for every design. Assume arbitrary costless reallocations, no restricted payment routes, no earmarking, no collection delays or borrowing limits, and that every cost is included in the same boundary. Then x is financially feasible if and only if C(x) ≤ F. If any design is feasible, every global minimum-cost design is feasible.

Proof: aggregate budget balance makes C(x) ≤ F necessary. With unrestricted pooled funding, it is also sufficient. For a minimum-cost x*, C(x*) ≤ C(x) ≤ F whenever x is feasible. This is an elementary diagnostic, not a claim that the proposition is itself a new research result.

For A identical holder caps b and sponsor cap s, the corresponding threshold is

    b_min(x; s) = max(0, [C(x) − s] / A).

Its ordering follows C(x). The meaningful output is a conditional financing frontier, not an unqualified scalar minimum. If holder budgets or payment rights differ, retain the actor vector and feasible set rather than silently averaging it.

A second useful diagnostic is price scaling: if C(x; q) = g(x) q e with all costs proportional to the same gas price q and exchange rate e, the ranking of C is unchanged for q > 0. Design crossings versus q require distinct non-gas costs, a fixed actor funding/collection constraint, or a genuinely different fee decomposition. A cheap-L2 multiplier alone adds no such mechanism.

## Reconciliation of the review's monetary comparison

Source: the unchanged `source_cohort_summary.csv`, scenarios `N16_zk_B{1,2,4}_d0_HIGH_weekly`. The archived workload observes A=4 wallets for 90 days. Let S be shared deployment and all publications, and h direct holder gas per wallet. This S is a horizon total, not measured initial liquidity.

| B | Shared gas S | Holder gas h | Total gas at A=4 |
|---|---:|---:|---:|
| 1 | 13,817,033 | 10,653,405 | 56,430,653 |
| 2 | 16,592,944 | 8,930,165 | 52,313,604 |
| 4 | 24,791,056 | 8,068,512 | 57,065,104 |

At the historical q0=0.130658648 gwei and EUR/ETH=2,164.73:

| Comparison | Direct holder difference | Full boundary per holder, A=4 | Full boundary per holder, A=32 projection |
|---|---:|---:|---:|
| B1 minus B2 | EUR 0.487402 | EUR 0.291117 | EUR 0.462867 |
| B2 minus B4 | EUR 0.243711 | EUR −0.335979 | EUR 0.171249 |

Thus EUR 0.49/0.24 is correct for direct holder costs. It is not the full lifecycle comparison. At A=4 B4 is more expensive than B2 once shared costs are allocated. Under fixed-workload linear replication, their shared-cost/holder-cost crossing is A≈9.5144; A=32 remains an unmeasured projection using these frozen shared costs. It is not an N=16/A=32 deployment. An actual A=32 run needs N≥32, such as N=128, and a new measurement of shared costs. These corrections do not remove the need for an early gate.

## Explicit restricted-payment scenario

For an existence test only, impose this architecture: a sponsor may fund shared operator costs but may not reimburse direct holder expenses, and holders may not fund the operator. Then

    feasible(x; s,b) iff s ≥ S(x) and b ≥ h(x).

This restriction creates a genuine two-dimensional frontier. It must be justified by the intended service arrangement before it can support a substantive result. It is not established by the traces.

Two deliberately constructed examples at q0 show why the answer is not necessarily “only expensive L1”:

| A | Sponsor cap s | Holder cap b | Cheapest total-cost B | Feasible B under restricted rule |
|---:|---:|---:|---:|---:|
| 4 | EUR 7.011920 | EUR 2.403959 | 2 | 4 |
| 32, projected | EUR 5.852540 | EUR 2.525814 | 4 | 2 |

The caps are derived from cost boundaries to construct examples, not taken from observed budgets. Allowing free transfers makes the total-cost optimum feasible again. These examples establish logical possibility; they do not establish prevalence, economic materiality, a market threshold in gwei, or a new scientific contribution. Do not select the final paper's constraints just because these examples yield a reversal.

## Reproducible pilot and its decision

Run `python go_nogo_pilot.py` in this directory. The script reads the frozen original summary, checks all anchor decompositions, then evaluates q={0,0.01,0.1,q0,1,10,100,1000} and A={4,32}. Sponsor caps in the diagnostic grid are {0,0.5,1,1.5,2} times the observed shared B2 cost at q0, clearly designated as scenario caps. It checks every budget frontier endpoint and midpoint under minimum possible-issuer-set requirements {1,2,4}. The script uses decimal arithmetic and checks zero prices, exact funding boundaries and zero/unlimited-holder funding boundaries.

Outputs: `cost_anchors.csv` (48 rows), `budget_frontiers.csv` (480 rows), `go_nogo_results.json`. The 3,924 combined threshold/privacy checks contain zero free-transfer reversals and 28 restricted-rule checks exhibiting reversal. That count is a diagnostic count, not a probability or a percentage of realistic deployments. Two examples are retained in JSON.

**Current decision:** no-go for a paper framed as “gas-price sensitivity plus freely reallocatable financing changes the optimal technical design.” Conditional go for investigating constrained financing and liquidity only after its restrictions are justified independently and the effect matters for a declared operational criterion. This pilot does not authorize the full campaign on its own.

## Broader questions worth testing before a large campaign

1. **Conditional financing frontiers and dominance.** Under which payment architectures does minimizing real resource cost also minimize each actor's required budget, and when do these objectives diverge? Report b_min as a function of sponsor commitment and permitted transfers; retain the no-reversal baseline.
2. **Funding timing and capital requirements.** Does an arrangement cover costs over 90 days but fail before subscription/per-use revenue arrives? Derive the smallest initial capital L needed to keep every actor/fund solvent along the event timeline. With deterministic cumulative costs C(t) and external receipts P(t), a pooled reference is L_min=max(0,sup_t[C(t)−P(t)]). Actor-specific restrictions require separate balances and permitted transfer schedules. Terminal gas totals cannot measure L_min.
3. **Revocation exposure and uncertainty.** At equal expected revocation cost, do correlated issuer updates produce materially different peak capital requirements, compensation shortfall risk or service interruptions? Distinguish a deterministic worst-case bound from a quantile requirement under an explicitly justified process. This extends the financing question beyond average euro premiums; overlap with the accepted ECON-07 compensation-fund work must be audited before claiming novelty.
4. **Privacy and freshness operating regions.** Determine which designs meet the stated issuer set and publication-to-rejection deadline while requiring the least lifecycle budget/capital, and when uncertain quantities change that choice. Model-only δ=3/7/14 can be studied with precise semantics; they must remain labelled as unavailable in the present contract.

These are candidate research questions, not four proven contributions. The minimum campaign should retain exact replay of the 54 traces, one selected A=32 EVM condition within the current δ cap, and the economics/financing diagnostic. Larger-scale EVM, changes to the δ cap, own-holder revocation/reissuance and an extensive mechanism comparison are outside this first campaign. Existing rejection/security tests are retained even when own-holder revocation is excluded from the research workload.

At the early gate, record: the independently justified rule and source; the technical admissible set; the funding/capital frontier; existence or absence of a design change; scale of any consequence (absolute cost, capital, shortfall or loss of admissibility); and uncertainty/robustness to supported assumptions. An empty effect or no-reversal finding may justify narrowing or integrating the work rather than a separate article. It does not justify manufacturing budget constraints.
