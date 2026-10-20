# PETs4DeFi — economic analysis of private eligibility checks

**ECON-03 · Nataliya. Technical inputs: Alexander (TECH-01).**

Estimate the additional user-transaction cost of specified privacy properties, and identify what further evidence is needed to judge their value. Compare an unchecked token deposit, signed eligibility checks and ZK proofs. Signed and ZK checks each have direct and cached access modes.

ZK hides the credential identifier, selected trusted issuer and private attributes from the on-chain presentation. Its pseudonym is application-scoped. Public wallets, transfers and timing remain visible. The eligibility policy and user workloads are synthetic.

## Inputs

| File | Use |
|---|---|
| [privacy_premium.csv](data/privacy_premium.csv) | Start here: 24 decisions comparing the cheapest measured signed and ZK access modes for each workload and policy. |
| [workload_costs.csv](data/workload_costs.csv) | The five methods, authorization counts and separate setup/operator budgets: 120 rows. |
| [input_register.csv](data/input_register.csv) | Record supported values or ranges, unit, source, date and scope. Leave unsupported inputs unknown. |
| [phase_sensitivity.csv](data/phase_sensitivity.csv) | Thirty rows showing the effect of shifting two revocations while keeping their count fixed. |
| [revocation_tradeoff.csv](data/revocation_tradeoff.csv) | Eight-row burst example for bounded revocation delays. |
| [event_costs.csv](data/event_costs.csv) | Measured gas per operation, sample counts, median and quartiles. |

## First deliverable

Prepare a **two-page note and the updated input register**. Begin with one scenario; there is no need to discuss every row.

1. Select `context_id = n100-K1-N1000-I4-L90-weekly-batched` and `policy = security`. This means 100 deposits, one service, 1,000 users, 90-day credentials, daily additions and weekly unrelated revocations. Use its five rows in `workload_costs.csv` and one row in `privacy_premium.csv`.
2. State which signed mode and which ZK mode minimize user-transaction gas. Report their difference in gas and under the two fee-price scenarios. Show eligibility overhead relative to unchecked deposits. Explain the counts of full authorizations and cache hits; keep setup and operator budgets separate.
3. Identify the missing costs that could change the decision. Complete the input register where evidence is available, and list the remaining data requests. Include evidence on revocation frequency and temporal clustering. Keep proof time separate from money unless a suitable valuation is supplied.

Three optional extensions are available after this first comparison: change the number of services or credential lifetime; inspect the phase table; inspect the burst table. Each should answer one specific question. Attach the note to the existing ECON-03 card and move it to Review. Alexander supplies technical measurements; no contract implementation is required from Nataliya. ECON-02 remains the separate Louafi exercise.

## Decision rule and cost boundary

For the **same workload and freshness policy**, select the cheaper measured direct/cached mode within each family. The primary difference is:

`minimum ZK user-transaction gas − minimum signed user-transaction gas`.

This selects the minimum **action and approval gas only**. It does not optimize total system cost: deployment, registry operation, issuance, witness delivery, user computation and failures must be assessed separately. Preserve the sign of the calculated difference. A positive difference is one component of the value needed to justify the specified privacy properties; it is not measured willingness to pay.

Direct-to-direct and cache-to-cache comparisons are technical controls. They remain in the [technical comparison table](../../examples/pets4defi_access_v2/results/policy_comparisons.csv); a cheaper ZK cache relative to a more expensive signed cache would not establish an advantage over the best signed option. The shared registry is not a minimal standalone signed deployment.

## Timing and policy assumptions

The main table contains `global` and `security`, both with immediate ordinary revocation. Under `global`, every publication invalidates both caches. Under `security`, signed access checks its own issuer/ID/policy status; ZK ignores additions but reacts to a shared security epoch. These are architectural choices, not universal costs of privacy.

Daily additions occur in every context. `none` means no unrelated revocations. The main `monthly` schedule uses days 30 and 60, aligned with the 30-day authorization TTL; treat it as an aligned control. The phase table instead fixes two events at days **15/45, 30/60 or 37/67**, with 90-day credentials and one or five services. Do not interpret equal costs in one alignment as evidence that monthly revocation has no effect.

The burst table studies delays of 0, 300 and 3,600 seconds. It distinguishes the cost for an unaffected user from the acceptance window of a revoked credential. It demonstrates a mechanism; it does not identify an optimal delay or an observed incident rate. Emergency changes remain immediate. Delays are engineering settings, not legal recommendations.

## Evidence

Recurring gas events have 30 local measurements; first-holder events and deployments have one. The population model has four issuers and 250 cohort credentials per issuer. Renewals publish four roots per round. The measured batch changes eight leaves; population scaling is a projection, not a load test.

EUR conversions use the recorded **CoinGecko quote of €2,164.73/ETH on 20 October 2026**; see [fx_quote.json](data/fx_quote.json). Fee p50/p90 are scenarios from the archived Ethereum fee window, not percentiles of quarterly bills. Full L2 fees and phone performance remain unmeasured.

[Provenance](data/provenance.json) · [Technical protocol](../../examples/pets4defi_access_v2/POLICIES.md)
