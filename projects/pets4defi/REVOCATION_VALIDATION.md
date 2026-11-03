# Revocation timing: complete local traces

Run on 3 November 2026 against unchanged contracts, circuit and dependency lock
from `d4031faa59ba5dd1781b663b676dc2c443bdc64f`. The protocol was written before
execution: [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md).

## Result

All 800 main deposit paths and 200 signed shared-invalidation control paths
match the independent recurrence. There are 30 fresh-holder state accesses,
four successful accesses in negative-control preparation, and seven included
reverts. The archive contains 1,242 receipts including setup and updates, and
38 synthetic proofs that also pass a separate saved-proof verification.

| Other revocation days | Signed full / hits | ZK full / hits | Signed gas | ZK gas | ZK minus signed |
|---|---:|---:|---:|---:|---:|
| 30, 60 | 3 / 97 | 3 / 97 | 8,227,683 | 7,780,373 | -447,310 |
| 15, 45 | 3 / 97 | 4 / 96 | 8,227,683 | 8,065,688 | -161,995 |
| 31, 63 | 3 / 97 | 5 / 95 | 8,227,683 | 8,348,215 | +120,532 |
| 7, 14, ..., 84 | 3 / 97 | 13 / 87 | 8,227,683 | 10,653,303 | +2,425,620 |

Totals include one approval and 100 successful deposits per method. Setup,
issuer updates, proving and rejected accesses are outside these user totals.
These are new receipt sums, not replacements for the historical economic input
means. The same two revocations can reverse the gas ranking when only their
timing changes. This is a finite counterexample, not an estimate of frequency
or a universal cost of zero knowledge.

The existing signed global-publication mode gives 3 full authorizations at
30/60 and 13 under weekly revocations (8,728,093 and 8,969,776 gas). Thus broad
invalidation also creates this effect without ZK. The diagnostic concerns
authorization counts; different status-check branches prevent attributing all
gas differences to one isolated factor.

## State-dependent gas

Historical mean-cost projections for the four ZK rows differ from the new
receipts by +54.4, -2,760.4, -8,363.2 and -8,313.6 gas. All ranking signs survive.
The maximum absolute relative difference is approximately 0.10% of the projected
ZK total. For all 27 observed later full ZK authorizations:

```
gasUsed = 342621 + calldataGas + 2800 * (changedUntil + changedSecurityEpoch)
calldataGas = 4 * zeroBytes + 16 * nonzeroBytes
```

Each change indicator is 0 or 1. The constant is empirical for this fixture.
An expiry-only renewal can leave the epoch unchanged. After credential expiry
caps the authorization deadline, another revocation can leave that deadline
unchanged. Rewriting an unchanged storage value saves 2,800 gas relative to
changing its nonzero value here, consistent with EIP-2200/EIP-2929. Proof and
signature bytes also change intrinsic calldata gas. The archived single mean
does not distinguish these states.

Five distinct synthetic holders supply new first/hit/renewal observations.
Combining their first-use ranges with all observed recurring-state ranges gives
ZK-minus-signed envelopes [-167882, -158940] at k=4 and [117433, 129211] at k=5.
These finite observed ranges preserve the sign; they are not confidence intervals.

## Proving and rejection evidence

The historical `results/server_prover.json` matches the current 7,409-constraint
circuit hash. It contains 30 fresh-process and 30 warm verified proofs, with
median fullProve times 1.884883 and 1.849473 seconds. Timers include witness
generation and artifact reads, exclude separate verification/startup; the OS
cache was not flushed. These are server observations, not device performance
or a monetary price. The older 496-constraint pilot's timings are inapplicable.
Durations in the new trace run are diagnostic only.

Seven included failures cover a used nonce, both exact-TTL caches, both caches
after paired own-credential revocation, revoked signed full authorization and
a pre-update ZK proof after authoritative revocation. The runtime checks the
decoded reason and unchanged token/deposit/nonce/cache state for every failure.
Correct issuer classification and timely paired publication remain assumptions.

## Reproduce and scope

From `examples/pets4defi_access_v2`:

```sh
npm ci
npm run setup
node scripts/revocation_validation.mjs
python3 scripts/check_revocation_validation.py
node scripts/verify_revocation_proofs.mjs
```

The recorded run uses Node 24.22.1, npm 11.9.0, Solidity 0.8.37, optimizer 200,
Cancun-target bytecode and an Osaka runtime. `allowBlocksWithSameTimestamp`
allows the specified update-before-access ordering at exact synthetic times.
Twenty credentials populate the fixture so the weekly trace removes twelve
distinct other leaves. Fresh phase 2 remains a one-process demonstration.

Files under `results/revocation_validation` preserve event/state traces, receipts,
calldata, synthetic proof inputs, proof objects, verification key, generated
verifier, source/setup hashes and an independently regenerated analysis.
`manifest.json` is the runtime evidence manifest; `analysis_summary.json` is
derived by the offline checker. New runs should use a fresh output directory
(`VALIDATION_OUT`) or retain the recorded directory separately first. Proof
randomness changes hashes/calldata, so fresh outputs need not be byte-identical.

Historical economic archives and inputs are unchanged. The later
[economic integration](economics/README.md) imports Nataliya Kolyada's attributed
computational core byte-for-byte and checks it in CI. Neither this validation nor
that integration resolves earlier dependency findings, replaces a colleague's
clean-environment run or establishes production security.
