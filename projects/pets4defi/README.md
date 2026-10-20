# PETs4DeFi — economic analysis of private eligibility checks

**ECON-03 · Nataliya. Technical inputs: Alexander (TECH-01).**

Estimate the additional cost of specified privacy properties and the conditions under which that cost is justified. The experiment compares an unchecked token deposit, signed eligibility checks and ZK proofs. Signed and ZK checks each have direct and cached access modes.

ZK hides the credential identifier, selected trusted issuer and private credential attributes from the on-chain presentation. Its pseudonym is application-scoped. Public wallets, transfers and timing remain visible. This is a synthetic eligibility experiment.

## Inputs

| File | Use |
|---|---|
| [workload_costs.csv](data/workload_costs.csv) | User transaction gas, authorization counts and separate setup/operator budgets. |
| [privacy_premium.csv](data/privacy_premium.csv) | Signed-minus-unchecked overhead and matched ZK-minus-signed differences. |
| [revocation_tradeoff.csv](data/revocation_tradeoff.csv) | Eight-row burst example: authorization cost versus the maximum cached revocation exposure window. |
| [input_register.csv](data/input_register.csv) | Add supported values/ranges, units, source, date and scope. Leave unsupported inputs unknown. |
| [event_costs.csv](data/event_costs.csv) | Measured operation costs, sample counts, median and interquartile range. |

## First deliverable

Prepare a **two-page note and the completed input register**. Start with one comparison; the full table is a sensitivity dataset, not a list of separate tasks.

1. In `workload_costs.csv`, select `context_id = n100-K1-N1000-I4-L90-weekly-batched` and `policy = security`. Compare its five methods. This is 100 deposits, one service, 1,000 users across four issuers, 90-day credentials, daily additions and weekly unrelated revocations. Use the two corresponding rows of `privacy_premium.csv` for direct and cached contrasts.
2. Change only the revocation schedule to `none` and `monthly`, then compare one versus five services while holding total deposits at 100. Explain differences through full authorizations and cache hits. Check 30-day credentials separately. Use `revocation_tradeoff.csv` for minute-scale delays: evenly spaced quarterly accesses cannot establish their effect.
3. Report the conditional value of privacy needed to cover its incremental cost. Identify which missing expenses could change the conclusion and provide sourced ranges where available. Keep proving time separate from money unless a suitable valuation is supplied.

Attach the note to the existing ECON-03 card and move it to Review. Questions and results belong on that card. No contract implementation is required from Nataliya. ECON-02 remains the separate Louafi reproduction exercise.

## Reading the comparisons

- **Eligibility overhead:** signed user transactions minus the matched unchecked deposits.
- **Privacy increment:** ZK minus signed user transactions with the same workload and access mode. Preserve negative differences if they occur; they are conditional implementation results, not proof that a whole ZK service is cheaper.
- **Separate budgets:** application setup and operator root/status publication costs are not included in the user-transaction difference. The shared registry is not a minimal standalone signed deployment.
- **Unknown expenses:** issuance, renewal, witness delivery, proving services, device costs and failure frequency. Unknown does not mean zero. Funding shares redistribute a specified bill; they do not change its total.

The primary workload has daily additions in every context; `none` means **no unrelated revocations**, not an unchanged registry. A 30-day authorization TTL is separate from credential validity. The synthetic population has 250 cohort credentials per issuer; daily single-leaf additions rotate across four issuers. A synchronized renewal publishes four replacement roots. The on-chain batch measurement changes eight leaves; scaling its fixed-size root publication to the model population is an explicit projection, not a 1,000-user load test.

## Freshness policies

| Policy | Cache behavior | Ordinary revocation delay |
|---|---|---:|
| `global` | Any publication invalidates both caches | 0 s |
| `security` | Signed checks its own ID; ZK ignores additions and reacts to security changes | 0 s |
| `delay_300` | Selective checks with a bounded ordinary-revocation delay | 300 s |
| `delay_3600` | Same policy with a longer bound | 3,600 s |

Emergency issuer/policy changes invalidate immediately. Recent-root presentation grace is separately fixed at 300 seconds in selective policies. An existing ZK cache may survive for Δ, while an old-root proof is bounded by both Δ and that 300-second grace. The direct `delay_3600` contrast is labelled as having different maximum presentation windows; do not interpret it as an equal-freshness privacy premium. An issuer's addition-only classification is trusted. These are engineering settings, not legal recommendations.

## Evidence and limits

Gas comes from local Ethereum-compatible execution receipts. Recurring events have 30 samples; first-holder events and deployments are single observations. Workload counts and risk exposure are model scenarios. Included-revert costs and a replacement proof are measured separately; occurrence frequencies remain unknown.

EUR figures use **€2,170/ETH as an assumption** and the archived Ethereum fee window. Fee p50/p90 are price scenarios from a block-weighted distribution, not percentiles of a user's quarterly bill. Full L2 fees and physical-device proof performance remain unmeasured. Do not infer demand, incident loss or whole-service profitability from these inputs.

[Provenance](data/provenance.json) · [Technical protocol and reproduction](../../examples/pets4defi_access_v2/POLICIES.md)
