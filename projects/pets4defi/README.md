# PETs4DeFi — economic analysis of private eligibility checks

**Task: ECON-03. Owner: Nataliya. Technical inputs: Alexander (TECH-01).**

Estimate the additional cost of specific privacy properties and identify the conditions under which that cost could be justified. Compare four access methods: signed credential or ZK proof, each with verification at every deposit or with a cached authorization.

ZK hides the credential identifier and the selected trusted issuer from the on-chain presentation. Public wallets and token transfers remain visible. These measurements concern a synthetic eligibility policy.

## Inputs

| File | Use |
|---|---|
| [event_costs.csv](data/event_costs.csv) | Measured gas for individual operations; distinguish first access, repeat access, cache hit and reauthorization. |
| [workload_costs.csv](data/workload_costs.csv) | Costs and authorization counts for 12 workload contexts and four access methods: 48 rows. |
| [privacy_premium.csv](data/privacy_premium.csv) | 24 matched ZK-minus-signed comparisons, with direct and cached access kept separate. |
| [input_register.csv](data/input_register.csv) | Complete missing inputs with a value or range, unit, date, source and scope. Leave unsupported values unknown. |

The dataset uses Ethereum L1 execution, 100 total deposits across one or five services, 1,000 users, a 90-day horizon, 30- or 90-day credentials, and a 30-day authorization TTL. Background registry updates are absent, weekly or daily. These are specified workloads, not observed user behavior.

EUR conversions use **€2,170/ETH as an assumption**, not a verified exchange-rate quote. Fee p50 and p90 are price scenarios derived from the archived block-level fee distribution; they are not percentiles of a user's quarterly bill. OP is excluded from monetary comparisons because its full transaction fees are unmeasured.

## First deliverable

Prepare a **two-page note and the completed input register**:

1. Start with 100 deposits, one service, 1,000 users, 90-day credentials and no background updates. Compare the four methods, separating user actions, allocated setup, registry updates and unknown costs. Report the matched privacy premium in gas and under the two fee-price scenarios.
2. Repeat for daily updates and then five services. Explain changes through the number of full authorizations and cache hits. Check how 30-day credential validity changes renewals and costs.
3. Answer the three research questions below and list the empirical inputs needed for the next calculation. Keep user proof time separate from money unless a sourced valuation is supplied.

## Research questions

- **Privacy premium:** what minimum value of the stated privacy properties would cover the additional cost? Report this threshold conditionally; demand and willingness to pay are unmeasured.
- **Revocation delay:** how should a maximum delay Δ be compared with authorization cost and exposure to use of a revoked credential? Alternative invalidation policies are unmeasured. Define the quantities needed; calculations of their effects await technical inputs.
- **Unknown costs:** what sourced ranges can be established for issuance, credential refresh, witness delivery and proof services? Record what each quote includes to avoid double counting. Phone proof performance remains a technical measurement task.

## Boundaries of the supplied data

1. **Coupled invalidation:** a ZK registry-root update resets both ZK and signed caches. The signed method is part of a shared registry, not an independently optimized signed service.
2. **Unbatched renewals:** each user's renewal produces a separate root publication. A 30-day credential has two renewal events in this 90-day workload. Batching is a separate scenario awaiting inputs.
3. **No ungated baseline:** deposit and approval costs are included. A deposit without an eligibility check has not been measured, so the absolute cost of compliance cannot yet be isolated.
4. **Successful accesses only:** stale-proof failures, retries and replacement proofs are not priced. The current-root requirement can cause such failures during registry updates.

Alexander owns contract changes, invalidation policies, batching, the ungated baseline and device/failure measurements. Nataliya owns the economic comparison and evidence for missing inputs; no contract implementation is required. Keep the work on the existing TECH-01 and ECON-03 cards. ECON-02 remains the separate Louafi reproduction exercise.

Technical provenance: [data/provenance.json](data/provenance.json).
