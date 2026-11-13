# ECON-08 first checkpoint — revalidated 13 November 2026

Nataliya Kolyada and Oleksandr Kuznetsov · PETs4DeFi · 13 November 2026

Please prepare one short design note with three tables. A first pass with open questions is enough. Post it on the ECON-08 Trello card when ready. The reference protocol, including the definitions and decision rule, is [ECON08_Technical_Protocol_v0_1.docx](ECON08_Technical_Protocol_v0_1.docx).

## Current technical checkpoint

This handoff accompanies the preserved EVM evidence and the strengthened audit. The [repository validation record](../VALIDATION.md) explains the exact historical source commits, proof-to-transaction checks and reproduction commands. [Pilot results](../RESULTS.md) and [cohort results](../COHORT.md) describe the measurement boundaries. Those technical links resolve inside the complete repository package. The standalone handoff ZIP includes the protocol and three CSV tables; ask Oleksandr for the complete technical package if needed. GitHub publication and the review link must be confirmed separately; this handoff does not imply that they are already available.

- EVM evidence: 32 native scenarios and 22 cohort scenarios, with 8,832 ordinary accesses in total. All 512 saved proofs and 10,627 signed transaction records passed revalidation on 13 November. This was an audit of existing observations, not a fresh measurement campaign.
- The corrected audit binds saved proofs and public signals to transaction calldata. Negative tests reject deliberately corrupted evidence.
- The W3C verifier now preserves millisecond validity boundaries; eight component tests pass. **The W3C timing table remains historical data from before this correction and is not a benchmark of the corrected code.** No new component timings or end-to-end comparison are claimed.
- Native gas, local W3C milliseconds/bytes, and unimplemented PRC/end-to-end costs belong to different measurement boundaries. Missing quantities are unknown, never zero.

Open [pilot_summary.csv](pilot_summary.csv), [cohort_summary.csv](cohort_summary.csv) and [w3c_component.csv](w3c_component.csv). These are unchanged copies of their original measured summaries. `SHA256SUMS` verifies the exact included protocol, instructions and CSV bytes. No software installation is needed for the first checkpoint.

## 1. What each mechanism guarantees

Start with page 2 of the protocol. Use the columns **mechanism and version | observer | information visible | trust and collusion assumptions | freshness clock and bound | availability | implementation status | source section**.

- Native ZK, B=1/2/4. The possible issuer set is 4/2/1 given the public group and other available metadata. The wallet and application-scoped nullifier can link accesses. State separately what the public chain, verifier, issuer and status service can observe. The freshness clock in the EVM pilot starts at authoritative publication.
- Signed EVM control. Record that it exposes the issuer and credential identifier. Use it as a diagnostic reference with a different privacy profile.
- W3C Bitstring Status List v1.0. Start with §§2.1–2.2, 3.2 and 6.2–6.3. Record which observers may see the list URL, index and retrieval patterns. The historical component measurements cover signing, verification, expansion and lookup on the earlier local implementation. Mark end-to-end freshness, network availability and integration costs as open.
- PRC. Record the paper's trust and collusion assumptions separately from the prototype's benchmark conditions. Mark integration and costs as open. Use CRSet only where it helps distinguish issuer-activity privacy from issuer hiding or holder unlinkability.

## 2. Map ECON-07 cost events to the new measurements

Open the accepted ECON-07 synthesis and reuse its K01–K16 identifiers and definitions. Use **existing K ID | mechanism | event | actor | unit | count or quantity | evidence | open input**. Keep issuer, holder and service rows identifiable.

| Event to map | Starting evidence | Accounting treatment |
|---|---|---|
| Initial roots | `pilot_summary.csv` and `cohort_summary.csv`, initial-publication columns | Issuer gas. Record each published root once. |
| Weekly revocations | `cohort_summary.csv`, `updates` and `status_publication` | Twelve measured publications in the weekly trace. No-update controls have zero publications by design. |
| Extra full authorizations | `cohort_summary.csv`, `authorizations` | Subtract the matched no-update count. Example at N=16, B=2, HIGH, zero delay: 28 − 12 = 16 extra authorizations across four wallets, or 4 per wallet. |
| Shared deployment | `cohort_summary.csv`, `operator_setup` | Charge the measured shared infrastructure once per run. The four-wallet result has no population extrapolation. |
| W3C list creation and lookup | `w3c_component.csv`, operation and size rows | Keep milliseconds and bytes in the W3C panel. End-to-end EVM gas, HTTP transport and issuer reporting delay are open inputs. |
| Issuance, hosting, witness delivery, reimbursement and settlement | ECON-07 ledger and protocol page 5 | Mark missing quantities or prices explicitly. Keep reimbursement and other transfers separate from resource use. |

The native pilot uses 8 synthetic credentials and one observed holder. The cohort experiment registers N=16, 128 or 512 synthetic credentials and measures four distinct holders, one per issuer, at each size. Compare counts and gas within the same workload, delay and privacy profile. `authorizations` in the cohort CSV is a four-wallet total. `holder_cohort` includes their approvals and successful accesses. `measured_boundary_gas` includes the four wallets and the measured shared EVM infrastructure. Keep all prices and unmeasured inputs explicit.

## 3. Outline three figures

| Figure | Axes and series | Data to use |
|---|---|---|
| Freshness and cost | x: permitted delay after publication. y: authorizations per wallet or gas. Series by ZK group count. Give the signed control its own panel. | N=16, HIGH, weekly runs. Use all three delays. Show gas by actor if plotted. |
| Effect of weekly revocations | x: mechanism. y: extra full authorizations per wallet. Compare weekly updates with the matched no-update control. | N=16, HIGH, zero delay. A separate panel can show B=2 at N=16/128/512 with four measured wallets at every size. |
| Feasible choices | x: allowed delay. y: minimum required issuer set. Mark feasible, infeasible and insufficient evidence. | Protocol pp. 2–3 plus the native results. Add a cost comparison only within a feasible set. Keep the W3C and PRC end-to-end cells open. |

Two short sentences on the implications and the main uncertainty are enough. The native weekly runs give 13, 7 and 4 full authorizations per wallet for B=1/2/4, versus 3 without updates. The result describes this schedule and shows how partitioning shifts effort and changes issuer visibility. Please flag any missing definitions or figures that need another technical measurement. Oleksandr will handle the code, correctness checks and further measurements. This checkpoint has no new implementation, manuscript or deadline.

## References

- ECON-08 Trello card https://trello.com/c/8i08gLxj
- Accepted ECON-07 synthesis https://docs.google.com/document/d/1hNPRNmUMegg88hn6mpCLO6pxj67zb48C7-m8wdO5FcE/edit
- W3C Recommendation https://www.w3.org/TR/2025/REC-vc-bitstring-status-list-20250515/
- EdDSA Data Integrity https://www.w3.org/TR/vc-di-eddsa/
- PRC https://www.usenix.org/conference/usenixsecurity26/presentation/edalatnejad
