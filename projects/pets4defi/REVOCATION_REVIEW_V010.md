# Revocation timing: review extension v0.10

This extension adds evidence for the interaction between shared invalidation and
rolling authorization expiry. It preserves the original contract, circuit, lockfile,
historical gas measurements and attributed economic core. It is a component study
with synthetic credentials, not a production deployment or an economic viability study.

## Evidence added

`examples/pets4defi_access_v2/results/revocation_review/` contains the final
successful extension, generated in an exported directory without `.git`:

- Three complete paired signed/ZK repetitions for each of 30/60, 15/45, 31/63
  and the separate twelve-revocation weekly reference: 2,400 access paths.
- Signed global-publication controls for all four schedules: 400 access paths.
- Enforced issuer partitions with 1, 2 and 4 registries: 300 access paths.
- 90 saved proofs; six mined rejection transactions; additional static checks
  for excluded-issuer publication and cross-group proof presentation.
- Raw receipts, transaction calldata, before/after states, setup metadata,
  verification key and SHA-256 manifest. The null Git head is intentional;
  the report records exact source-file hashes and the preceding integration commit.

All 3,100 access paths agree with the event recurrence. All 90 proofs verify
under the saved key. Own-revocation failures preserve balances, cache and nonce.
These are automated checks, not independent human review or a cryptographic audit.

| Schedule | ZK full authorizations | ZK total gas, three repetitions | Shared signed count |
| --- | ---: | ---: | ---: |
| 30/60 | 3 | 7,780,313–7,780,349 | 3 |
| 15/45 | 4 | 8,065,640–8,065,676 | 4 |
| 31/63 | 5 | 8,348,131–8,348,179 | 5 |
| Weekly | 13 | 10,653,279–10,653,315 | 13 |

Every selective signed trace uses three authorizations and 8,227,683 gas.
Totals include approval and 100 deposits. Three repetitions vary proof encoding
under one local setup; they are not independently sampled workloads. The shared
signed control has a different checking branch and identifies the **count** effect,
not the signed/ZK gas premium.

## Exhaustive and stochastic models

`scripts/revocation_model.py` saves its results in `results/revocation_model/`.
For all 3,916 unordered pairs of distinct integer days 1–89, with 100 accesses
at 0, 0.9, …, 89.1 days and TTL 30 days:

| Full ZK authorizations | Date pairs | Share | Historical fixed-mean ZK minus signed gas |
| --- | ---: | ---: | ---: |
| 3 | 6 | 0.1532% | −447,121.4 |
| 4 | 1,675 | 42.7732% | −158,991.6 |
| 5 | 2,235 | 57.0735% | +129,138.2 |

The 30/60 case is rare, not a representative baseline. Four-authorizations cases
also favor ZK; lower ZK gas does **not** require exact coincidence with renewal.
The shares describe a stipulated uniform grid, not deployed revocation prevalence.

An exact combinatorial dynamic program counts all fixed-m subsets for m=0…12.
A separate age/count dynamic program and finite-horizon renewal equation model
homogeneous Poisson updates. If h=0.9 days, p=1−exp(−λh), and s=ceil(30/h)=34,
the next authorization interval is W=min(Geometric(p),s). With f the distribution
of W, u[0]=1 and u[i]=sum(f[l]*u[i−l]); the expected count is sum(u[0:100]).
This includes the initial authorization and multiple updates coalescing between
accesses. It does not approximate a finite horizon by 100/E[W]. The parameter
90λ is an expected 90-day event count, although the last access is at day 89.1.

Five standard-library tests compare the grid with a separate event-driven cache,
fixed-count DP with exhaustive small subsets, and both Poisson calculations with
all binary update patterns on short grids. They also check coalescence and TTL boundaries.

## Majority cost and average cost are different claims

For all 27 original and 72 new later full ZK authorizations, the exact observed
expression is:

`gas = 342621 + calldata_gas + 2800*(changed_deadline + changed_security_epoch)`.

The uniform two-day grid's mean difference is +5,012.8 gas with historical fixed
means. Applying the observed state expression and pooled first-use/calldata
ranges gives a mean sensitivity envelope of −1,041.1 to −693.3 gas instead.
The signs of the three count classes remain unchanged within that envelope.
Thus the majority result does not establish a positive average cost premium.
The envelope is a projection from finite observed ranges, not a confidence
interval or 3,916 additional EVM traces.

The fixed-mean expected-gas crossing at 90λ≈2.0267 is likewise a conditional
projection boundary, not a state-corrected or empirical profitability threshold.

## Measured issuer partitions

The same two publications occur at day 31 in issuer 3 and day 63 in issuer 1.
The holder belongs to issuer 0. B=2 uses groups {0,1}/{2,3}; B=4 uses singletons.
Every registry permanently disables out-of-group issuers, and their attempted
publication is rejected. Merely leaving an issuer root unpublished would not
enforce a partition; that design is not the reported alternative.

| Groups | Public issuer options | Relevant days | Full authorizations | User gas | Fixture setup gas | Two publication gas |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| 1 | 4 | 31/63 | 5 | 8,348,179 | 10,641,015 | 980,636 |
| 2 | 2 | 63 | 4 | 8,060,064 | 14,948,654 | 725,354 |
| 4 | 1 | None | 3 | 7,774,749 | 23,912,642 | 597,712 |

There is one complete trace per partition. Setup includes common components,
all registries/ZK gates, initial publication, exclusions and one signed diagnostic
gate in every configuration. No whole-system optimum or amortization is claimed.
The gate exposes the issuer group; B=4 loses issuer hiding. Issuer cardinality is
not anonymity entropy, particularly with unequal credential populations.

Under an independent equal-rate Poisson illustration with 12 expected global
updates, E[K] is 12.3373, 7.4350 and 5.2284 for B=1,2,4. Thinning the update rate
by B does not divide the full-authorization count or gas by B.

## Conditional financing

`schedule_economics.csv` applies the same historical unchecked baseline, unit
gas, p50 fee and dated EUR/ETH rate consistently to all four schedules.
Gas-only user-payment parity alpha is 120.11%, 106.33%, 95.39% and 52.32%,
respectively. Values above 100% require no reimbursement for gas-only parity.
At alpha=0.5 and zero other net expense, per-proof expense ceilings are €0.14698,
€0.10005, €0.07189 and €0.002574. These are conditional budgets, not measured
proving prices, realized transfers, demand or service profit.

## Reproduce

From `examples/pets4defi_access_v2`:

```sh
python3 scripts/check_revocation_validation.py
python3 scripts/check_revocation_validation.py --out results/revocation_review
python3 -m unittest discover -s scripts -p test_revocation_model.py -v
python3 scripts/revocation_model.py --out /tmp/pets4defi-model
diff -r results/revocation_model /tmp/pets4defi-model
npm ci
node scripts/verify_revocation_proofs.mjs
node scripts/verify_revocation_proofs.mjs --out results/revocation_review
```

For fresh EVM execution, run ordinary `npm run setup`, use `PTAU_FILE` with the
exact pinned public transcript, or explicitly use `node scripts/setup.mjs --local-demo`.
The saved extension used the last option: single-process phase-one and phase-two
contributions, with no production security claim. This option never silently
replaces the public transcript. Then:

```sh
VALIDATION_OUT=/tmp/pets4defi-review node scripts/revocation_review.mjs
python3 scripts/check_revocation_validation.py --out /tmp/pets4defi-review
node scripts/verify_revocation_proofs.mjs --out /tmp/pets4defi-review
```

The old runner also accepts `VALIDATION_OUT`; Git absence is now non-fatal.
The checker takes `--out` (or `VALIDATION_OUT`) and writes derived JSON only
when `--analysis-output` is supplied. Historical runner/package source snapshots
permit exact provenance checks of the unchanged original evidence.
Node.js 24.22.1, npm 11.9.0, Solidity 0.8.37, Cancun bytecode and Osaka runtime
were used locally. Broader dependency issues are not declared resolved.
