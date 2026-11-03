# Independent review response: v1 to v2

Verdict: **v1 was a useful measurement smoke test, but was not an adequate privacy/economics foundation for a paper.** It remains under `../pets4defi_access/` as historical evidence. V2 changes the comparison before extending economic claims.

| Review point | Assessment and v2 response |
|---|---|
| v1 adds no demonstrated privacy beyond a signed bit | Agreed. V2 uses private credential and issuer membership, policy predicates and a scope pseudonym. The signed baseline is also registry-wide/reusable. Wallet-level unlinkability is explicitly not claimed. |
| Per-action verification is an architectural choice | Agreed. Four matched treatments: signed direct, signed cached, ZK direct, ZK cached. Cached access checks current epoch and expiry. Root churn is a workload variable rather than a hidden assumption. |
| 1/10/100-gwei scenarios do not represent current fees | Agreed that hypothetical sensitivity values must not be called observed prices. V2 separates measured gas from prices. A bounded read-only RPC collector archives timestamped fee evidence when available and records unavailable data honestly. The quoted October figures are not adopted without verification; base fee is not total effective fee. |
| L2 needs different fee accounting | Agreed. V2 includes local OP Stack execution. Execution gas is **not** a full rollup transaction fee: L1 data and operator charges are separate missing components. |
| Ganache and Windows dependency lock harm reproducibility | Fixed: v2 uses pinned Hardhat/EDR and explicit runtime hardforks. V1's malformed transitive lock is repaired without changing historical circuit/results. Root Python dependencies no longer contain a Windows local editable path. CI exercises Node22/npm10 and Node24/npm11. |
| Age threshold is a weak DeFi research scenario | Agreed. V2 demonstrates trusted-issuer membership, minimum tier, allowed jurisdiction and current active status. The policy is synthetic; no legal equivalence with AML/KYC is asserted. Allowlist membership is not described as a general sanctions non-membership proof. |
| Six server samples omit user costs | Agreed. V2 provides raw 30-run server cold/warm measurements and a separate real-browser/physical-phone harness. Browser/phone results remain missing until executed on an accessible device. Server timing is never relabelled as mobile UX. |
| Prior scenario table mostly repeated a linear identity | Agreed. V2 derives cache misses from an ordered access/status/expiry trace, allocates fixed deployment over users/apps, accounts for renewal root publication and distinguishes total usage from usage per service. Alpha only allocates cost; it does not change social cost or establish demand. |
| Extra actionBinding is unnecessary in the pinned stack | Reproduced: the same proof fails after changing the public request even when the original R1CS has no constraint referencing it. V1 without actionBinding has 256 rather than 496 constraints. See the retained public-input experiment. V2 uses one real scope pseudonym output and explicitly range-constrains the request. |
| Public per-gate revocation leaks and scales poorly | Replaced for ZK with authenticated hierarchical active-set roots. Public issuer root updates remain visible, current witness delivery remains an implementation requirement, and global cache invalidation is measured/modelled. |
| Single-process trusted setup | Improved phase-1 provenance through a pinned public ceremony transcript. Two local phase-2 contributions are still one trust domain, explicitly not independent. Production ceremony remains a release blocker. |
| Need static analysis and adversarial token/expiry tests | Added circuit/contract reviews, explicit test evidence and narrowly documented static-tool findings. Malformed proofs, exact expiry boundaries and token rollback/reentry are exercised by the harness. |

## What is a sound basis now

Use v2 as a **reproducible architecture-cost experiment with explicit privacy properties**. The principal hypothesis is: how do verification placement, credential lifetime, status-update frequency, number of services and shared fixed costs change the cost of the specified privacy features?

Do not claim that ZK necessarily becomes cheaper than a reusable signed credential as the number of services grows. Both treatments can reuse one issuance. A comparison against repeated institution-specific KYC is a separate baseline and requires measured onboarding prices, actual interoperability assumptions and data-retention obligations. Unknown witness distribution, issuer operations, user computation and L2 fee components remain explicit missing terms.

## Deliberate next stages

1. Execute the existing browser harness on an ordinary laptop and a physical phone, retaining device/browser versions and raw samples.
2. Measure full rollup fees for serialized transactions under a pinned network/oracle state, including L1 data and operator fees.
3. Implement the issuance and witness-update service; measure update traffic and evaluate batch/epoch policies before making issuer-unobservability claims.
4. Add an independently specified signature-in-circuit treatment (EdDSA for a native ZK credential, or P-256 for a compatible credential profile). The on-chain P-256 precompile does not make P-256 cheap inside a ZK circuit. Do not substitute a different proof system or signature curve and call it the same privacy protocol.
5. Broaden proof-system comparisons only after identical statements, trust assumptions, circuit semantics and client hardware are fixed. Groth16/PLONK/FFLONK is a separate experimental dimension, not an automatic quality improvement.

Primary-source links and the fee evidence status are in `SOURCES.md`; actual measurements and limitations are in `results/` and `README.md`.
