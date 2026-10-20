# PETs4DeFi — economic analysis of private eligibility checks

**Economics: Nataliya (ECON-03 → ECON-04 → ECON-05). Technical inputs: Alexander (TECH-01).**

Research question: how do private eligibility checks, repeated use and revocation requirements change access costs, who pays them, and what user benefit and service margin would justify their use? The supplied measurements establish technical inputs. Nataliya develops the economic ledger, conditional thresholds and sensitivity analysis.

Compare an unchecked token deposit, signed eligibility checks and ZK proofs. Signed and ZK checks each have direct and cached modes. The **economic regimes** are B0: selected signed access, user-funded; B1: selected ZK access, user-funded; B2: the same ZK implementation with part of its declared access-cost pool paid by the service. Technical methods and financing regimes are different dimensions.

ZK hides the credential identifier, selected trusted issuer and private attributes from the on-chain presentation. Its pseudonym is application-scoped. Public wallets, transfers and timing remain visible. The eligibility policy and user workloads are synthetic.

## Inputs

| File | Use |
|---|---|
| [ECONOMIC_PROTOCOL.md](ECONOMIC_PROTOCOL.md) | Start here: economic boundary, B0/B1/B2, equations, fee rule, sweep and acceptance criteria. |
| [event_ledger.csv](data/event_ledger.csv) | Event → trigger/count → executor/payee → initial payer/final bearer → source and double-count rule. |
| [frequency_workload_costs.csv](data/frequency_workload_costs.csv) | Five technical methods at 1, 10 and 100 deposits; new-user workloads, not observed behaviour. |
| [frequency_event_counts.csv](data/frequency_event_counts.csv) | Exact modeled counts of approve, first/repeat access and cache events, reconciled to each workload. |
| [frequency_decisions.csv](data/frequency_decisions.csv) | Cheapest signed and ZK user-transaction choices at each frequency. |
| [economic_sweep_plan.csv](data/economic_sweep_plan.csv) | Fifteen economic scenarios: three frequencies × five user shares. This is a plan, not completed profitability results. |
| [privacy_premium.csv](data/privacy_premium.csv) | Sensitivity inputs: 24 signed/ZK decisions for service count, credential lifetime and revocation policy. |
| [workload_costs.csv](data/workload_costs.csv) | The five methods, authorization counts and separate setup/operator budgets: 120 rows. |
| [input_register.csv](data/input_register.csv) | Record supported values or ranges, unit, source, date and scope. Leave unsupported inputs unknown. |
| [phase_sensitivity.csv](data/phase_sensitivity.csv) | Thirty rows showing the effect of shifting two revocations while keeping their count fixed. |
| [revocation_tradeoff.csv](data/revocation_tradeoff.csv) | Eight-row burst example for bounded revocation delays. |
| [event_costs.csv](data/event_costs.csv) | Measured gas per operation, sample counts, median and quartiles. |

## First deliverable

Prepare a **two-page note, event ledger and updated input register** in ECON-03. Begin with one scenario; there is no need to discuss every row or implement the full model yet.

1. Select `context_id = n100-K1-N1000-I4-L90-weekly-batched` and `policy = security`. This means 100 deposits, one service, 1,000 users, 90-day credentials, daily additions and weekly unrelated revocations. Use its five rows in `workload_costs.csv` and one row in `privacy_premium.csv`.
2. State which signed mode and which ZK mode minimize user-transaction gas. Report their difference in gas and under the two fee-price scenarios. Show eligibility overhead relative to unchecked deposits. Explain the counts of full authorizations and cache hits; keep setup and operator budgets separate.
3. Use the event ledger to distinguish external costs, user-to-service fees and reimbursement. Confirm B0/B1/B2, the allocation pool and fixed fee rule in the economic protocol. Record service revenue and fixed expenses as unknown parameters where evidence is absent; report required margin rather than assumed profitability.
4. Complete supported input values/ranges and list remaining data requests. Include issuance, witness delivery, active user time and revocation timing. Unknown prices remain parameters; they do not prevent a clearly bounded first analysis.

After review, **ECON-04** implements the ledger with two hand-worked checks. **ECON-05** runs 1/10/100 deposits × 0/25/50/75/100% user funding under the same fixed fee rule. The two archived Ethereum fee scenarios reprice these 15 cases; they are not independent workload experiments. Then choose one focused lifetime, service-count, phase or burst extension if it changes a conclusion. Do not combine all dimensions at once.

Attach the ECON-03 result to its existing card and move it to Review. Alexander owns contracts, ZKP/privacy changes, technical validation and missing device/L2 measurements. For a technical request, state the economic question, missing event/parameter, needed unit/range and affected conclusion on the current card; no ZKP implementation is required from Nataliya. ECON-02 remains a separate bounded Louafi reproduction exercise, not a source of DeFi willingness-to-pay estimates.

The frequency inputs can be regenerated from the archived measurements, without Node or a new proof run, using Python 3.10+ from the repository root:

```sh
python3 projects/pets4defi/scripts/build_economic_inputs.py
```

## Decision rule and cost boundary

For the **same workload and freshness policy**, select the cheaper measured direct/cached mode within each family. The primary difference is:

`minimum ZK user-transaction gas − minimum signed user-transaction gas`.

This selects the minimum **action and approval gas only**. It does not optimize total system cost: deployment, registry operation, issuance, witness delivery, user computation and failures must be assessed separately. Preserve the sign of the calculated difference. A positive difference is one component of the value needed to justify the specified privacy properties; it is not measured willingness to pay.

Direct-to-direct and cache-to-cache comparisons are technical controls. They remain in the [technical comparison table](../../examples/pets4defi_access_v2/results/policy_comparisons.csv); a cheaper ZK cache relative to a more expensive signed cache would not establish an advantage over the best signed option. The shared registry is not a minimal standalone signed deployment.

## Timing and policy assumptions

The main table contains `global` and `security`, both with immediate ordinary revocation. Under `global`, every publication invalidates both caches. Under `security`, signed access checks its own issuer/ID/policy status; ZK ignores additions but reacts to a shared security epoch. These are architectural choices, not universal costs of privacy.

A **cache hit** is a successful deposit that reuses an existing authorization without verifying a new signature or ZK proof. It still pays deposit gas and performs action, expiry and live status checks. In `security`, signed caches check the public credential's own status, whereas ZK caches check their stored security epoch. An unrelated revocation can therefore invalidate the ZK cache while leaving the signed cache usable. `cache_hits_per_user` includes both `cache_hit` and `cache_hit_grace`; `old_epoch_grace_hits_per_user` is a subset, not an extra group of deposits. A grace hit accepts an older security epoch within its original deadline; it does not renew that deadline.

The cache-related privacy increment depends on **access spacing relative to revocation spacing**, together with authorization TTL, credential expiry, event phase and the selected access method. It is not a monotonic effect of transaction frequency alone; total cost also depends on the number of actions. In the one-service weekly-revocation trace, 10 deposits are 9 days apart and the ZK cache has no hits; 100 deposits are 0.9 days apart and produce 87 ZK cache hits. A single initial deposit has no reuse opportunity. With round-robin use of K services, the interval between visits to the same service is K times the overall access interval.

Daily additions occur in every context. `none` means no unrelated revocations. The main `monthly` schedule uses days 30 and 60, aligned with the 30-day authorization TTL; treat it as an aligned control. The phase table instead fixes two events at days **15/45, 30/60 or 37/67**, with 90-day credentials and one or five services. Do not interpret equal costs in one alignment as evidence that monthly revocation has no effect.

The phase mechanism is the overlap between expiry and invalidation: both may be handled by one full authorization at the next access. That authorization restarts the rolling TTL, capped by credential expiry, so moving a revocation can also change later expiry-triggered authorizations within the finite horizon. For one service, the supplied ZK-cache traces require three full authorizations for the 30/60 revocation schedule versus four for either shifted schedule, although all schedules contain exactly two revocations. This is a timing effect, not a change in revocation frequency.

The burst table studies delays of 0, 300 and 3,600 seconds. It distinguishes the cost for an unaffected user from the acceptance window of a revoked credential. It demonstrates a mechanism; it does not identify an optimal delay or an observed incident rate. Emergency changes remain immediate. Delays are engineering settings, not legal recommendations.

## Evidence

Recurring gas events have 30 local measurements; first-holder events and deployments have one. The population model has four issuers and 250 cohort credentials per issuer. Renewals publish four roots per round. The measured batch changes eight leaves; population scaling is a projection, not a load test.

EUR conversions use the **CoinGecko web quote of €2,164.73/ETH observed on 20 October 2026**, retrieved at 19:56:58 UTC; see [fx_quote.json](data/fx_quote.json). The market tick timestamp is unknown: retrieval time is not a quote timestamp, daily close or daily average. This retained observation is a conversion scenario, not a realized transaction price. Fee p50/p90 are scenarios from the archived Ethereum fee window, not percentiles of quarterly bills. Full L2 fees and phone performance remain unmeasured.

The grant connection is private, reusable eligibility verification for WP3/WP4 (T3.4/T4.2), including revocation and gas/latency. This local deposit fixture is an input to the integrated zk-KYC prototype, not completion of D4.1. Ethereum EUR figures are a public-network deployment scenario, **not the operating budget of the grant's Besu testnet**, whose test-token gas price may be zero. Hosting, proving and provider costs still need their own accounting.

[Measurement provenance](data/provenance.json) · [Frequency-input provenance](data/economic_inputs_manifest.json) · [Technical protocol](../../examples/pets4defi_access_v2/POLICIES.md)
