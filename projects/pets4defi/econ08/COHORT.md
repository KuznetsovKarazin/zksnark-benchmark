# ECON-08 issuer-balanced cohort

Protocol v0.1, population extension. In each scenario a fresh local Hardhat Osaka EVM registers 16, 128 or 512 synthetic credentials, equally distributed across four issuers. Four distinct wallets, one per issuer, execute the observed workload using leaf 0. The other credentials contribute to the issuer roots. The Merkle path remains fixed at ten levels and each issuer tree retains capacity for 1,024 credentials.

The public fixture seed is `ECON08-cohort-v1`. Each run uses the same 90-day horizon, 30-day authorization lifetime, zero root presentation grace and eligibility policy as the native pilot. Weekly revocations occur on days 7 through 84. They rotate issuers 0, 1, 2 and 3, using leaf 1 in the first rotation, leaf 2 in the second and leaf 3 in the third. The update precedes access at the same second. The four observed wallets are eligible throughout. A no-update control isolates the additional authorizations in each weekly trace. Timing from these parallel runs is diagnostic only. The baseline timing experiment used three dedicated sequential sessions.

## Archived evidence

The 22 unchanged run folders are in [results/econ08_cohort/runs](../../../examples/pets4defi_access_v2/results/econ08_cohort/runs). The original source commits are preserved in [ECON08_source.bundle](ECON08_source.bundle). The current stronger checker is used with the original source directory selected by each report; see [VALIDATION.md](VALIDATION.md).

## Run and audit

Use the commit recorded in the measurement's `report.json` to run or audit that result. Starting from the repository root:

```sh
cd examples/pets4defi_access_v2
npm ci
npm run setup
node scripts/econ08/run_cohort.mjs --population 16 --mechanism zk_B2 --delta 0 --workload HIGH --out results/local/cohort-demo
python3 scripts/econ08/check_cohort.py --source-root . results/local/cohort-demo
node scripts/econ08/verify_proofs.mjs results/local/cohort-demo
```

Use a new output directory per run. Supported mechanisms are `zk_B1`, `zk_B2`, `zk_B4` and `signed_control`. Delays are `0`, `3600` and `86400` seconds. `--no-updates` selects the control. `LOW` executes one access per wallet and `HIGH` executes 100 per wallet. The signed control produces no Groth16 proofs and uses the receipt audit alone. The independent Python audit checks the schedule, receipts, cache behavior, transaction and proof links, and actor totals. The Node verification independently checks the archived Groth16 proofs.

## Results

22 scenarios passed the receipt and event audit, covering 7,216 successful accesses. All 392 cohort proofs verified independently. The main N=16 HIGH comparison covers the four mechanisms at each delay with weekly updates and a no-update control per mechanism at zero delay. The size extension uses ZK B=2 at zero delay with both workloads. An additional signed LOW run checks the four-wallet setup and publications after the last access.

| N=16, HIGH | Authorizations per holder without updates | Weekly, 0 s | Weekly, 3,600 s | Weekly, 86,400 s |
|---|---:|---:|---:|---:|
| ZK B=1 | 3 | 13 | 13 | 13 |
| ZK B=2 | 3 | 7 | 7 | 7 |
| ZK B=4 | 3 | 4 | 4 | 4 |
| Signed control | 3 | 3 | 3 | 3 |

All four holders have the same counts within each row and scenario. Weekly updates add 10, 4 and 1 authorizations per holder for B=1, B=2 and B=4 respectively at zero delay. The hour-long and day-long grace periods shift some authorization timestamps without changing the 90-day counts at this access cadence. The original two-update pilot's reduction from 5 to 4 for B=1 at 24 hours therefore depends on the update schedule. Delta is measured from authoritative publication.

| N=16, HIGH, weekly, zero delay | Four holders | Operator setup | Initial roots | Weekly publications | Measured total |
|---|---:|---:|---:|---:|---:|
| ZK B=1 | 42,613,620 | 6,472,975 | 1,460,416 | 5,883,642 | 56,430,653 |
| ZK B=2 | 35,720,660 | 11,044,408 | 1,196,586 | 4,351,950 | 52,313,604 |
| ZK B=4 | 32,274,048 | 20,140,288 | 1,064,670 | 3,586,098 | 57,065,104 |

Values are gas. B=2 has the lowest measured sum among these three variants and a potential issuer set of two, conditional on metadata. A requirement to hide the issuer among all four admits only B=1 in the current native implementation. The holder-side reduction from B=2 to B=4 comes with higher setup gas and issuer disclosure.

At N=16, 128 and 512, ZK B=2 still needs seven authorizations per holder in HIGH and one in LOW. HIGH holder totals are 35,720,660, 35,720,408 and 35,720,648 gas respectively. Registry occupancy varies while proof depth, update schedule and measured cohort size are fixed. These measurements do not vary the number of active wallets or estimate the resulting system load.

## Cost boundary

- Holder gas includes approvals and accesses for the four measured wallets.
- Setup covers all registries and gates, partition setup, one shared Poseidon and one shared verifier for the ZK variants. The fixture token, funding and gate bootstraps are recorded separately.
- Initial roots and all 12 weekly publications are charged once per scenario. The signed control uses the same registry/publication boundary as ZK B=1 and exposes issuer and credential identity.
- The measured boundary covers the four wallets and shared infrastructure. Extending those holder costs to every issued credential requires a population model and additional workload evidence. Off-chain status publication, external adapters, issuance, hosting and economic prices remain open inputs.
