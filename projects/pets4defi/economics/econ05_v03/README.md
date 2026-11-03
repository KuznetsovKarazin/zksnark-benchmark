# PETs4DeFi — ECON-05 Core Financial Sweep v0.3

**Research author:** Nataliya Kolyada  
**Scientific reviewer and technical source owner:** Oleksandr Kuznetsov  
**Status:** submitted for independent review; ECON-04 accepted.  
**Date:** 22 October 2026.

This package carries out the agreed **3 activities × 5 user-funded shares = 15 economic cases**, repriced at **2 archived Ethereum gas price scenarios**: 30 numeric rows. It includes **exactly one completed, source-reconciled technical extension**: the fixed-count, 2-revocation phase sensitivity. All 30 rows of the uploaded phase source are preserved; only the 15 K=1 method rows (three phases × five technical methods) are used to compute the six 3-phase × 2-fee outputs. This is a different event schedule from the twelve-weekly-revocation core. No 1,000-deposit work or other extensions were performed.

## Reproduce numeric results (stdlib only)

```
python3 economic_sweep.py
python3 derive_review_extensions_v03.py
python3 independent_central_result.py
python3 -m unittest -v test_econ04.py test_sweep.py test_review_v03.py
```

This regenerates `results/econ05_sweep_30rows.csv`, `results/b0_reference_6rows.csv` and `results/run_metadata.json`. No third-party library, network request or smart contract/proof execution is needed.

`economic_model.py` is the **unchanged accepted ECON-04 v0.1 implementation**. `economic_sweep.py` reuses its workload selector, event-cost checks, version pins, account-conservation function and unit conversions. Inputs are the three frozen technical source CSVs plus the original `economic_sweep_plan.csv` (all 15 scenarios independently cross-validated for p50 and p90). Every run writes input byte-level SHA-256 and configuration SHA-256.

## Package contents

- `econ05_config.json` — declared scope, n=1/10/100, alpha grid, p50/p90 and symbolic unknowns.
- `economic_model.py` — approved ECON-04 foundation (unchanged).
- `economic_sweep.py` — main one-command model; pure stdlib.
- `test_sweep.py` — 9 new tests; the accepted original v0.1 used its own 12 earlier tests.
- `inputs/*.csv` — exact frozen source tables and economic sweep plan.
- `results/econ05_sweep_30rows.csv` — all numerical network components and symbolic margin/benefit thresholds.
- `results/thresholds_30rows.csv` — explicit quantified minimum margin and user benefit inequalities per priced case, plus allocation identity.
- `results/phase_selected_source_verified_6rows.csv` — source-verified per-phase, per-price ZK/signed selection, aggregate gas, cash reimbursement and user network difference; strictly TWO unrelated revocations, not twelve weekly ones.
- `independent_central_result.py` — source-CSV-only reproduction of one nominated n100 α=.5 p50 result (no import of the ECON-05 model).
- `results/b0_reference_6rows.csv` — comparison signed reference for each n × fee scenario.
- `results/run_metadata.json` — commit IDs supplied by reviewer, input content hashes, precise configuration and scope limits.
- `ECON-05_Approved_15_Cases_2_Prices_v0.3_Nataliya_Kolyada.xlsx` — fully formula-linked Excel presentation with original 30 cases, explicit symbolic thresholds, accounting invariance, source-verified phase extension, central result and source provenance.
- `ECON-05_Research_Note_v0.3_Nataliya_Kolyada_EN.md` — scientific interpretation, 30-row core and six controlled phase-price results, source boundaries and caveats.
- `figures/*.png` — three separate finished charts requested for the scientific review.
- `make_figures.py` — OPTIONAL chart script, uses matplotlib (not needed to reproduce core results).

## Accounting boundary

C0 is the common user-paid unchecked-deposit gas, and A_j is the incremental user-action-and-approval gas for the selected signed or ZK method relative to C0. B0 is signed/user-funded, B1 is the ZK/user-funded alpha=1 endpoint, and B2 is the selected ZK with modeled conditional cash-equivalent service reimbursement R=(1-alpha)A_ZK. **The user wallet still prepays full gas**, and there is no implemented cashback or paymaster. Issuance/witness/proving, root/deployment/other operator budget, failures, refund payout cost and other external resource costs are NOT in A. They are still **unknown** and must not be mistaken for zero.

Minimum net margin requirement is `m_required = s_other + R - f + F/N` (N>0). The reported R is the **known network-only incremental service coverage component**, not a profitability estimate. All such comparisons remain conditional on non-gas revenue/cost inputs and cash-equivalent refund feasibility.

## Review protocol

Review numerical reconciliation, source provenance, α boundaries, B0 reference, sign of conditional network-payment difference, p50/p90 repricing ratio, and the stated unknowns. Do not describe auto-tests as independent expert review. Direct the broader 1,000-deposit/timing questions to Oleksandr under TECH-01, after this core review.

AI assisted with coding, checking, graphics and writing; the numeric technical gas inputs were supplied by the project and are not newly measured by this package.

## Scope closure and source validation

The 15×2 agreed core is ready for independent review. Exactly one optional extension is **completed and numerically reconciled against the uploaded source**: revocation phase days 15/45, 30/60, 37/67 with two revocations; n=100, K=1, L=90, TTL=30, horizon=90 days. Technical totals and full-auth/hit counts come from `inputs/phase_sensitivity.csv` (30 original source rows; SHA-256 `70ab143e0951cd391571ac972b4a5ccf20ac861ab96c9e9d2811ea7cecdfd3b0`). The 6 priced K=1 rows are in `results/phase_selected_source_verified_6rows.csv`; no K=5/lifetime/burst/extra frequency axis was run. Synthetic results are not observed user behavior, actual demand or proven overall maximum/minimum timing outcomes. Reviewer approval remains pending.

To reproduce: `python3 derive_review_extensions_v03.py` re-derives 30 threshold expressions and the 6 phase-price results from the supplied source CSV, checked gas table and pinned prices. The main `economic_model.py` remains byte-identical to accepted ECON-04.

The term "privacy premium" is avoided as a figure title. The gas-only difference is one component of required incremental user value, not measured WTP. The accounting conservation and fee invariance checks are identities, **not discoveries**.

## Workbook and figures regeneration

`python3 build_workbook_v03.py` builds the checked v0.3 spreadsheet using the **retained v0.2 workbook template** in `build_resources/`; the old template is a build prerequisite and must NOT be cited as the current scientific result. The v0.3 sheet contains source-verified six-row phase comparisons and the accepted 30-case basis. This optional build step requires `artifact_tool`. `python3 make_figures.py` regenerates the three core figures using matplotlib (optional for the numeric script).
