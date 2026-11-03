# Public-input binding review — 20 October 2026

The claim that an unconstrained public `requestHash` must have a zero Groth16 verification-key coefficient is **false for the tested toolchain**. Circom preserves the public wire, and snarkjs adds public-input terms when constructing the QAP. Removing the v1 `actionBinding` hash therefore did not allow the same proof to be accepted with a changed request hash.

## Executed experiment

Toolchain: Node.js 24.19.0; `circom2` npm package 0.2.23 / Circom compiler 2.2.3; `snarkjs` 0.7.6; `circomlib` 2.0.5; BN254 Groth16. All circuits were compiled with `--O2 --inspect --r1cs --wasm --sym`. Each used a separate local demonstration proving key and verification key, with the existing local phase-2-ready Powers of Tau file. No production setup is claimed.

For each case, one proof was generated with `requestHash = 123`. The exact same proof was then verified with that public signal changed to `124`, keeping every other public signal unchanged.

| Circuit | R1CS constraints | Constraints containing requestHash | Request IC is zero | Original verifies | Changed request verifies |
| --- | ---: | ---: | --- | --- | --- |
| Toy square, unused public requestHash | 1 | 0 | No | Yes | No |
| Toy square, private linear alias of requestHash eliminated by O2 | 1 | 0 | No | Yes | No |
| v1 copied into scratch with actionBinding hash/output removed | 256 | 0 | No | Yes | No |
| Unmodified v1 copied into scratch | 496 | 2 | No | Yes | No |

The toy circuit is `square <== secret * secret` with `requestHash` declared public. The second case also assigns `unusedAlias <== requestHash + 1`; O2 removes that unused private relation. Compiler inspection warns about the unconstrained public signal in the applicable cases, but its public witness slot and nonzero IC point remain.

The evidence is consistent with installed `snarkjs/src/zkey_new.js`: after reading the original constraints, it adds A and IC terms for every public signal. `groth16_verify.js` uses `IC[0] + sum(publicSignals[i] * IC[i+1])`. A truly zero IC point would make that contribution independent of the corresponding value, but that condition did not occur here. See also the [Circom simplification documentation](https://docs.circom.io/circom-language/circom-insight/simplification/) and [snarkjs 0.7.6 setup implementation](https://github.com/iden3/snarkjs/blob/v0.7.6/src/zkey_new.js).

To reproduce after installing dependencies and generating the local v1 setup:

```sh
node scripts/review_binding.mjs
```

The review script copies circuits and writes experimental artifacts into a new temporary directory. It reads the existing `build/pot_final.ptau`; it does not change the v1 circuit, setup files or measured results. It reports its output directory and exits unsuccessfully if the expected verification behavior changes.

## Interpretation for the next version

The extra Poseidon hash costs 240 R1CS constraints and one public output in this example. It can serve as explicit circuit-level context binding, but should not be justified as a repair for a reproduced snarkjs public-input substitution vulnerability. These mutation tests are a focused regression check, not a general proof of protocol security or an audit of other proving backends.

A nullifier and an action binding answer different questions. A nullifier such as `Poseidon(secret, scope)` identifies reuse within a defined scope. The contract must enforce the intended scope and consumed-nullifier rule. Including the whole request in that nullifier changes the policy: different requests produce different nullifiers. An action hash instead describes the exact recipient, amount and other execution context; the contract must recompute and check it. v1 has no nullifier and enforces replay protection using the holder's sequential nonce.

If v2 constrains its request hash using a bit decomposition, describe this as an explicit range constraint. The contract still needs to compute the same canonical hash representation and compare it with the verifier input. Re-test context substitution using the final circuit and verifier.

## npm 10 clean-install repair

On Linux with npm 10.9.9, the original lockfile failed `npm ci` with `EBADPLATFORM` for `fsevents@2.3.2` (Darwin-only). The same failure occurred with `--omit=optional` and with npm 11.9.0. Its nested Ganache lock entry was marked extraneous, not optional.

Using npm 10.9.9, the lockfile was regenerated with:

```sh
npm install --package-lock-only --ignore-scripts --no-audit --no-fund
npm ci --no-audit --no-fund
```

The generated cleanup removed 317 extraneous entries; the other 192 entries were unchanged, with no additions or version changes. A clean npm 10 installation then succeeded with lifecycle scripts enabled. No platform override, forced install or manual optional-dependency relabeling was used. The circuit and historical measurement files remain unchanged; the changed lock hash will correctly invalidate the setup cache on a future normal setup run.
