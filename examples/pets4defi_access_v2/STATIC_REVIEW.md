# Solidity static and manual review — v2 synthetic pilot

Review date: 2026-10-20. This is a bounded implementation review, not a production security audit, certification, or real-world KYC validation. The scope is `AccessGate`, `AccessRegistry`, the synthetic token, the generated Groth16 verifier, and the adversarial token fixture.

## Reproducible commands and findings

Tools actually used: Slither **0.11.6**, crytic-compile **0.4.2**, and native Solidity **0.8.37+commit.f401782d.Linux.g++**. The npm benchmark also locks solc to 0.8.37. Own-contract pragmas were pinned to exactly 0.8.37; the snarkjs-generated verifier keeps its generator's pragma and is compiled with the same pinned compiler.

From this example directory, after `npm ci` and `npm run setup`:

```sh
python3 -m venv .review-venv
.review-venv/bin/python -m pip install slither-analyzer==0.11.6
python3 scripts/static_checks.py --slither .review-venv/bin/slither --solc /path/to/native/solc-0.8.37
```

Obtain the native compiler from the Solidity project's v0.8.37 release and verify its reported version. The script scans **all five targets with all default detectors**; it does not suppress detectors or exclude the test fixture/generated verifier. Raw JSON, logs, versions, source hashes, and an aggregate summary are written under `results/static_analysis/`.

| Target | High | Medium | Low | Informational |
|---|---:|---:|---:|---:|
| AccessGate | 0 | 0 | 3 | 1 |
| AccessRegistry | 0 | 0 | 0 | 0 |
| MockToken | 0 | 0 | 0 | 0 |
| Generated Verifier | 3 | 0 | 0 | 46 |
| AdversarialToken, including inherited MockToken | 0 | 1 | 3 | 1 |

**The script returns exit code 1 for this reviewed snapshot**, because High/Medium findings remain in the unfiltered report. Exit 1 means findings require review; exit 2 means missing inputs or an analyzer/compiler error. Do not describe this result as an all-green static scan or add a blanket `|| true` CI waiver.

Manual dispositions, without altering or suppressing raw findings:

- **Generated verifier, three High `incorrect-return` findings:** Yul helpers deliberately execute `mstore(0, 0); return(0, 0x20)` when a public signal is outside the scalar field or a curve precompile fails. That exits the external verifier with ABI-encoded `false`. It does not return an authorization success or skip a successful-verification check in AccessGate. The outer function has no subsequent state cleanup whose omission would alter this behavior. This disposition is specific to the generated source hash below; a new template or modified helper needs review again. Runtime checks should cover a valid proof, a malformed curve point, and an out-of-field signal directly against the verifier, in addition to Gate-level checks.
- **Adversarial fixture, one Medium `reentrancy-no-eth`:** the fixture intentionally calls an arbitrary configured target while its transfer is in progress. Its low reentrancy/event diagnostics and missing-zero-target check, plus informational low-level-call diagnostic, are expected features of the attack fixture. It is never the ordinary asset and is not suitable for deployment.
- **Gate, three Low `timestamp`:** expiration/window checks intentionally use the chain timestamp. They provide block-time validity, not exact wall-clock guarantees. This is appropriate for the pilot's day-scale windows; sequencer/validator time assumptions remain relevant to production designs.
- **Gate assembly:** the sole assembly block parses the exact-length ECDSA signature. A 65-byte length check precedes it; low-s, v in {27,28}, and nonzero recovery checks follow it.
- **Generated informational findings:** assembly, the upstream pragma range, and generated naming conventions. The verifier was scanned rather than omitted.

## Manual security checks

No concrete authorization bypass was found in the reviewed Gate/Registry/MockToken snapshot. This conclusion is limited to the modeled synthetic token and trusted registry deployment.

- **Signed path:** the EIP-712 domain binds the credential to chain ID and registry; the holder must be `msg.sender`; active issuer, current policy version, public credential revocation, eligibility, the not-before time, expiration, low-s recovery, and nonce are checked. Registry-domain credentials can intentionally be reused across gates sharing that registry. Transaction signatures provide holder authorization for the amount; the reusable issuer credential is not an amount-specific signature.
- **ZK path:** all eight public signals are constrained to the scalar field at the Gate boundary. Registry root, policy root, minimum tier, application scope, validity window and request hash must match the current context before verifier acceptance. The request hash binds chain, gate, holder, token, amount, nonce, registry epoch and validity window. The first successful use binds that scope nullifier to its calling wallet.
- **Cached path:** authorization remains wallet-bound and requires the current registry epoch and unexpired window. Any issuer-root, policy, public-revocation, or disable update increments the global epoch and invalidates all caches. This conservative global invalidation has an economic cost; it must not be modeled as selective invalidation.
- **Atomicity and reentry:** every external deposit path uses the same non-reentrancy guard. Nonce, deposit balance, cache and nullifier binding are written before the token call; a false-return or reverting transfer reverts the transaction and rolls back those writes. Calls to the registry/verifier/hasher are view/static calls. The deliberately adversarial token is for exercising swallowed and propagated callback failures.
- **Registry authority:** only the assigned issuer can replace its own credential root; only the owner can change policy or permanently disable an issuer. Registry publication authenticates an issuer's assertion, not the truth of its KYC process.

## Limits requiring explicit interpretation

1. The asset is an exact-transfer synthetic token. `transferFrom(true)` is trusted; a fee-on-transfer, rebasing, or malicious token can make credited deposits differ from received tokens. There is no general safe-token integration, balance-delta check, lending behavior, redemption, or withdrawal in this pilot.
2. Signed public-ID revocation and hidden credential removal are separate representations. `revokePublic` invalidates caches but does not remove a credential from an issuer's hidden tree; that requires an authenticated issuer-root update. Neither operation alone proves a matched end-to-end revocation procedure for both representations.
3. A holder can share a secret. The scope nullifier binds its first use to a wallet within a gate, but does not prove a real person's identity, prevent all secret-sharing, or hide wallets/token movements. Small public synthetic fixture sets provide no empirical anonymity claim.
4. The owner and issuers are trusted governance roles; this bounded registry has four fixed issuer slots and no issuer rotation/reactivation, timelock or production key-management protocol.
5. Static analysis does not establish circuit soundness, semantic equivalence of the two eligibility paths, browser security, data availability, RPC fee correctness, or production privacy. Those require separate checks. The setup uses a public phase-1 powers-of-tau transcript followed by **two local phase-2 contributions from one process**; they are not independent participants and do not make a production-safe ceremony.
6. Timing and gas are local measurements. Passing tests and reviewed static findings do not establish deployed Ethereum/OP behavior or real KYC compliance.

## Reviewed source fingerprints

| File | SHA-256 |
|---|---|
| `contracts/AccessGate.sol` | `fe65e159a7b9ade8556e43e6908d92551103cb66676efa9539e1ac51d99ca41c` |
| `contracts/AccessRegistry.sol` | `d381a9e3bbf8a2a76fef0b9e5eee970e17104c94e04a0c4f21ecccf27e6e36be` |
| `contracts/MockToken.sol` | `93317c1308cffe63e4133a17502a4933ccd14e207b2f96a28453b6f681a99c60` |
| `build/Verifier.sol` | `ae236ac2c67ff95297aa539e7ffa7fb92610698e7bca8afaa0620b43e8b3f933` |
| `contracts/AdversarialToken.sol` | `ed71c870a625fad4bc109b4ab68d35a1597b589801ce9880a032354f82a06d0d` |

A regenerated verifier changes with the local phase-2 contribution. Its fingerprint must be recorded again when the setup changes; the script records hashes for every run and rejects concurrent source changes.

## Dependency advisories and narrow repairs

`npm audit --omit=dev` was run against the actual v2 lock on 2026-10-20. The initial report contained 20 affected dependency nodes: 6 High, 2 Moderate and 12 Low (no Critical). These are dependency-tree counts, not 20 independent flaws.

The exact overrides now in `package.json` address the three High root causes while preserving all seven direct dependency versions:

| Dependency | Patched version | Reason |
|---|---|---|
| `tmp` through solc | 0.2.7 | Fix path traversal/type-confusion advisory GHSA-7c78-jf6q-g5cm; retain solc 0.8.37 |
| `underscore` through snarkjs → bfj → jsonpath | 1.13.8 | Fix recursion denial-of-service advisory GHSA-qpx9-hpmf-5gmw |
| `ws` under @ethersproject/providers | 8.21.0 | Fix memory disclosure/exhaustion advisories GHSA-58qx-3vcg-4xpx and GHSA-96hv-2xvq-fx4p |

`npm ls ws tmp underscore` exits 0 after installation and shows only the intended patched versions (Hardhat retains its newer ws 8.22.0). The final audit reports **0 Critical, 0 High, 0 Moderate, and 15 Low affected nodes**. The remaining tree derives from [elliptic GHSA-848j-6mx2-7j84](https://github.com/advisories/GHSA-848j-6mx2-7j84) in circomlibjs's ethers 5 dependency. It is retained and disclosed; replacing that major dependency requires separate compatibility/security work. This is not a clean audit and does not establish exploitability or non-exploitability for the application. The unfiltered `npm audit` still exits 1 due to the Low findings.

## Node 22 / npm 10 compatibility check

An isolated directory ran **Node v22.23.3 / npm 10.9.9** and a fresh `npm ci` successfully against the final patched lock: 198 packages installed; lock SHA-256 `81726c28590f4bfd03fb9bba8bba8cc7140e9c77eacbee83e90ab68ba2cd9165`. The working example's dependencies were not deleted for this clean-install test.

Before those three transitive repairs, the same Node/npm pair also initialized the Hardhat `l1` provider (chain ID 31337) and completed a fresh `npm run setup`: 7,409 constraints, checked public phase-1 transcript hash, two local phase-2 contributions, `ZKey Ok!`, and exported verification artifacts. That earlier setup used lock SHA-256 `541e292ba0c56e98d791a8b106d741f79a34cb80bbe374645c5920ba7c0514b4`; it is recorded as a setup compatibility check, **not a complete final-lock demo result**. The final lock changes require regeneration of the matching setup manifest before benchmark publication.
