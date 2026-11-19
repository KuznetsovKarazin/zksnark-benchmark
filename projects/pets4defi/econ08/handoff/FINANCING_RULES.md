# Financing rules v0.4

These two fixed policy families make the liquidity question testable. They are research assumptions, not properties guaranteed by Ethereum. Their values and coverage are fixed before comparisons. Nataliya maps costs and funding to these rules; she does not have to invent a payment architecture.

## 1. Fixed families and accounting boundary

| Item | SELF: direct payment, no reimbursement | PM: prepaid holder-operation sponsorship |
|---|---|---|
| Holder approval and successful access operations | Each holder funds its own account | One prepaid pool funds the covered holder operations |
| Full authorization, reauthorization and cache hits | Include the actual transaction fee of each | Same operations and access times; include their fees |
| Shared deployment and publications | Separate operator and issuer role accounts | Same separate accounts, outside the holder pool |
| Compensation or later reimbursement | None in the primary policy | None in the primary policy |
| Source of operating-account funding | Each actor's explicitly identified treasury | Pool treasury for holder fees; separate treasuries for shared accounts |

The trace diagnostic includes four initial holder approvals and all 400 HIGH access operations per run. It excludes token deposit principal, fixture funding/minting and diagnostic transactions. Issuance/KYC and off-chain costs remain separate unknowns. Role accounts follow the source ledger's economic actor labels; issuer-labelled transactions in the fixture may share an administrative signer. The diagnostic does not establish separate actors' observed solvency.

The PM family is motivated by prepaid sponsorship of user operations. The existing benchmark contains ordinary EVM transactions, not an ERC-4337 implementation. Its actual gas cannot establish smart-account, validation, bundling, post-operation, stake or funding-transaction costs. The v0.3 `operator_only_sponsor` scenario pays shared operator costs and is **not** the PM family. Keep it as historical analysis only. Free unrestricted transfers remain a theoretical control.

## 2. Timeline and replenishment are fixed

Use the same workload, successful-access times, event order and refill phase for SELF and PM. The common lifecycle origin is `t0 = report.context.base − 3600`, matching fixture initialization before the first setup transaction. First user access occurs at `t0 + 3600`; initial approvals occur earlier and are not moved after their actual time. The comparison horizon ends 90 days after first access.

Primary policy: fund each account to a constant target K at t0, then restore it to K at t0+24h, t0+48h, and so on before the end of the declared horizon. At an exact tie, a refill occurs before the debits. The target is constant for the full lifecycle. A refill is the amount needed to restore the balance, not a fixed daily contribution. Empty intervals are retained. Sensitivities change only the interval to seven days, or prohibit all refills after t0. These schedules are hypothetical operational policies; no standard mandates daily replenishment.

For a matched comparison, apply that same refill grid to each SELF holder account and to the PM holder pool. Keep operator/issuer accounts separate under the same declared grid. Initial and refill transfers come from an identified external treasury. Report its required cumulative funding; do not silently assume unlimited funds. This first spending-floor calculation assumes zero transfer delay and omits unmeasured top-up transaction fees. It does not prove a deployable service can maintain the schedule.

Authorization expenses are triggered by actual accesses. A status publication can invalidate cached eligibility, but does not cause every holder to transact immediately. Use the recorded subsequent access and cache/TTL state; retain publications as separate shared expenses. Do not manufacture synchronous reauthorizations at publication times.

## 3. Distinguish cost, operating liquidity and validation reserves

Let c_k be an actual monetary debit and i_k an external receipt available at the declared event order. For fixed receipts, the minimum initial cash that prevents a negative balance is

    L_cash = max(0, max_prefix Σ(c_k − i_k)).

No customer revenues, reimbursements or operating-account refunds are assumed in the trace pilot. With only nonnegative debits and no refills, L_cash equals the total horizon spending. Reordering that fixed set of expenses alone cannot lower this total.

For reset-to-target replenishment, let W_j be the nonoverlapping intervals starting at the fixed refill grid. With nonnegative debits, zero delay and no admission reservation, the hindsight minimum target is

    K_cash = max_j Σ_{k in W_j} c_k.

This target is a spending floor. Initial transfer is K_cash. Each later refill restores the current balance to K_cash. Report separately: total resource spending C; initial transfer; sum of later refills; gross treasury funding G; and ending balance E. The reconciliation is G − C = E. Unused deposit remains an asset. It is not a second resource expense, nor is replenishment a resource saving. The treasury has to supply G as scheduled; its own initial capital depends on independently specified incoming funds and cannot be inferred from the operating-account target alone.

Even a single EOA transaction can require more balance before execution than its eventual actual fee. A paymaster likewise needs a sufficient deposit at validation. For a **serial** diagnostic only, if an operation requires reserve M_k immediately before execution and then settles to actual fee c_k, the starting-funds requirement is

    K_serial = max_k [Σ_{j<k} c_j − I(t_k−) + M_k]_+.

M_k depends on gas limits, fee caps and validation rules; it must not be replaced by receipt gas used. ERC-4337 can validate several UserOperations before execution and reserve funds across the bundle. The serial equation does not certify that process. No M_k or bundle reservation is measured here. Deposits for gas, locked stake and their financing costs must be recorded separately. See the [ERC-4337 specification](https://eips.ethereum.org/EIPS/eip-4337), definitions, EntryPoint verification, and paymaster extension; consulted 13 November 2026.

## 4. What is measured now, and what remains open

`trace_inputs.json` is extracted from eight archived N=16, A=4, HIGH, δ=0 runs: B=1/2/4 and signed, each with weekly updates and its matched no-update control. Source report, access and receipt archives are checked against their original hashes. The extraction preserves 3,390 included debit records. This is new accounting of existing observations, not new EVM evidence. It reprices gas with historical q0=0.130658648 gwei and EUR/ETH=2,164.73; the quote is not current. `liquidity_diagnostic.py` and nine boundary/conservation tests reproduce the output.

The primary daily holder-pool target for ZK is about 2.313 million gas, or EUR 0.654 at q0 for four holders. It is set by startup approvals and first authorizations. It is effectively unchanged between weekly and no-update traces and equals the sum of SELF holder targets. Thus the archived primary case does **not** establish a new revocation-driven liquidity effect or a pooling advantage. Seven-day targets are about 3.936 million gas and are also startup-dominated. Small gas differences across equivalent traces must not be interpreted as an economic effect.

A fixed secondary description excludes only the first daily window, ending at t0+24h, and reports all later daily-window debits. Weekly B1/B2/B4 maxima are 1,693,460 / 1,117,194 / 829,043 gas, versus approximately 1,411,800 gas in the no-update controls. This shows that the later debit pattern can change in both directions, while the full-lifecycle target remains startup-dominated. It does not replace the primary target, alter the refill policy or establish a safe deposit. The cutoff is fixed, not selected to amplify an effect. Seven-day later-window diagnostics use their own first seven-day window and remain separately labelled.

The next predeclared question is whether separating an explicitly funded startup stage from continuing service produces useful reserve conditions under realistic access phases and matched TTL phases. Declare that policy and comparison before extending the workload. Also test refill delay, fees, uncertain prices and validation reserve requirements. No result should presume synchronized demand, reduced capital or a change of optimal B. Own-holder revocation, reissuance and longer-delay contract changes remain outside the first campaign; existing correctness tests remain intact.

## 5. Nataliya's first checkpoint

Use SELF and PM above with the primary 24-hour rule. For one B=2 weekly trace and its no-update control, map the ledger to the funding accounts, distinguish expense from transfer and retained balance, and identify which missing price/receipt/reserve input prevents each claim. Start with the supplied actual-debit floor, then state the additional data needed for a deployable prefunding bound. The seven-day and no-refill columns are sensitivities; no new mechanism selection or crypto implementation is requested. A budget ceiling, if later used, is a clearly labelled financing scenario or a sourced commitment, not willingness to pay.
