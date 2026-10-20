# Circuit and protocol review — 20 October 2026

This is a bounded source review and local compiler/witness check of the synthetic
v2 experiment. It is not an independent security audit, formal verification,
production approval, or an empirical measurement of anonymity. No confirmed
critical authorization bypass was found in the reviewed circuit and gate logic;
that statement applies only to this review's scope and assumptions.

## Reviewed artifacts and tools

The circuit uses `Access(10,2,3)`: credential depth 10, issuer depth 2, jurisdiction
policy depth 3. The source SHA-256 values at review time were:

| Artifact | SHA-256 |
|---|---|
| `circuits/access.circom` | `d4c64f58cb8dc74d10478c5fdd097344fb9f6d08643e47a9328f2da211188ba6` |
| `contracts/AccessRegistry.sol` | `d381a9e3bbf8a2a76fef0b9e5eee970e17104c94e04a0c4f21ecccf27e6e36be` |
| `contracts/AccessGate.sol` — after activation-time correction | `fe65e159a7b9ade8556e43e6908d92551103cb66676efa9539e1ac51d99ca41c` |
| `scripts/fixtures.mjs` | `dfde1142257f6578e1d9760f3b5040357052194b3f66ea5686490711b1e242f0` |

Runtime: Node.js 24.19.0; Circom compiler 2.2.3 from `circom2` npm package
0.2.23; snarkjs 0.7.6; circomlib 2.0.5. Compiler output was isolated in `/tmp`.
From this example directory, the equivalent command is:

```sh
mkdir -p /tmp/pets-v2-circuit-review-build
node node_modules/circom2/cli.js circuits/access.circom --r1cs --sym --O2 --inspect -l node_modules -o /tmp/pets-v2-circuit-review-build
```

Compilation succeeded: **7,409 nonlinear constraints**, zero linear constraints,
7 public inputs, 1 public output, 37 private inputs, 7,424 wires and 21,773 labels.
There were **11 CA02 warnings**: nine in `Access(10,2,3)` for unused-in-parent
bit-output arrays, and two in the library's `LessThan(8)` / `LessThan(64)` components.
The nine arrays belong to `boundedIssuer`, `boundedTier`, `boundedMinimum`,
`boundedJurisdiction`, `boundedRequest`, and `date0` through `date3`.

These outputs are deliberately not consumed by the parent. The `Num2Bits`
components still enforce Boolean bits and reconstruction of the input internally;
the warning does not mean the input is unconstrained. Inspection of the optimized
R1CS found `main.requestHash` at witness index 8 in one constraint (zero-based
constraint index 975). Range checks, comparison inputs and Merkle direction bits
were reviewed together; the comparator inputs have explicit matching bit bounds.

**Circomspect was not run.** No Circomspect, Cargo or Rust compiler was installed.
The official GitHub releases API returned no binary assets for v0.9.0, v0.8.1 and
v0.8.0. Its documented installation requires Cargo. Compiler `--inspect` is a
narrower check and is not reported as a substitute for Circomspect.
Primary references: [Circomspect](https://github.com/trailofbits/circomspect) and
[official releases API](https://api.github.com/repos/trailofbits/circomspect/releases).

## Independent witness checks

The same source was compiled to WASM in `/tmp`. An isolated harness used the
repository's fixture builder and `calculateWitness(input, true)`. All 12 cases
matched their expected result:

| Cases | Result |
|---|---|
| Valid credential; shortened valid window ending exactly at credential expiry | 2 accepted |
| Request hash equal to `2^248`; minimum tier above credential tier; non-Boolean credential path direction; wrong public registry root | 4 rejected |
| Window before credential activation; window beyond credential expiry; empty window | 3 rejected |
| Authenticated credential with forbidden jurisdiction; authenticated low-tier credential; removed leaf against the current registry root | 3 rejected |

These are generated-witness checks, not a proof of absence of alternate malicious
witnesses and not a substitute for end-to-end proof and contract tests. This
review did not generate a second v2 trusted setup or duplicate the benchmark's
proof/transaction suite.

## Request binding, caching and revocation

- The public request hash is the low 248 bits of Keccak over canonical ABI fields:
  chain, gate, sender, token, amount, action nonce, current registry epoch and
  validity window. The gate recomputes it and checks all public signals are in the
  scalar field. The circuit explicitly constrains the 248-bit range. The deployed
  verifier must correspond to this circuit and public-signal ordering; verification
  of a previously generated proof with changed public inputs must be tested.
- The scope pseudonym is `Poseidon(secret, scope)`, where scope depends on chain,
  gate and the fixed policy identifier. It stays stable within that application,
  including across policy-version changes. It is **not** a one-use nullifier.
  Sequential per-wallet action nonces prevent replay. First-use binding prevents
  later use of the same pseudonym by another wallet in that gate, but does not
  prevent secret sharing, a first-use race, or sharing across distinct gates.
- Cached authorization is per wallet, expires at its recorded end time and must
  match the current global epoch. Registry changes invalidate caches; updating
  state before token transfer is safe only with the implemented reentrancy guard
  and transaction rollback. The token experiment assumes ordinary exact-amount
  ERC-20 behavior, not fee-on-transfer or rebasing accounting.
- `revokePublic(id)` marks the B0 signed ID revoked and increments the epoch. It
  **does not remove a B1 hidden credential leaf**. B1 revocation requires the issuer
  to remove that leaf and publish the new authenticated issuer root. Conversely,
  a hidden-root removal alone does not revoke a B0 signed ID. The source documents
  these separate representations; comparisons must apply and charge for the
  appropriate operation on each path. No single cross-representation atomic
  revocation mechanism is implemented.
- Every issuer-root change, issuer disable, public revocation and policy change
  increments one global epoch. Even an unrelated issuer's change invalidates all
  caches. A trusted issuer can cause refresh churn by repeatedly changing its own
  root. Availability and reuse economics therefore depend on the aggregate update
  rate, not just the focal user's credential status or the nominal TTL.

The initial B0 snapshot had no signed activation time, whereas B1 enforces
`notBefore <= windowStart`. This review identified the discrepancy for pre-issued,
future-valid credentials. It was corrected by adding signed `uint64 validFrom`
and a `CredentialNotYetValid` check. Follow-up source inspection confirmed that
the Solidity struct, EIP-712 type string, struct hash and benchmark signing type
agree; the benchmark also includes a future-valid negative case. Execution of
that contract case belongs to the benchmark's integration results, not the
independent WASM checks above. B0 intentionally relies on issuer-attested
eligibility for a policy version; B1 proves tier and jurisdiction predicates on
committed attributes.

## Privacy and trust boundaries

The intended benefit is reduced disclosure of the selected issuer, credential
attributes, exact credential validity dates and membership witness in the gate
proof transcript, under the proof system and commitment assumptions. Public
windows still disclose bounds on credential validity. The public registry shows
which issuer slots and roots exist, and timing or witness-distribution metadata
may identify the selected issuer. The public policy and accepted predicate also
reveal information about eligible attributes.

There are **four issuer slots and two populated credentials per issuer: eight
synthetic credentials total**. Depth 10 provides capacity for 1,024 leaves per
issuer, not a measured anonymity set of that size. Fixture secrets and salts are
public deterministic constants. This dataset demonstrates execution and transcript
structure; it does not provide real-user confidentiality or measure anonymity.
Actual anonymity depends on populated eligible credentials and adversary knowledge.

Wallet addresses, token flows, amounts and transaction timing remain public. Using
the same wallet across gates remains linkable despite different scope pseudonyms.
There is no claim of anonymous payments, identity nontransferability, resistance
to issuer/prover collusion, or legal KYC compliance. Holder-wallet binding is a
first-use application rule, not proof of a unique person. There is no recovery or
reset mechanism for that permanent binding.

Issuers must honestly establish attributes and publish current active membership
roots; the circuit cannot establish the truth of off-chain checks. The owner is
trusted for policy changes and issuer disabling. Deployment must supply the correct
Poseidon implementation and verifier. The local phase-2 setup is a demonstration,
not an independently contributed production ceremony. B0 uses EOA ECDSA signatures;
contract-wallet issuer signatures via EIP-1271 are not implemented.

## Feasible authorization periods

For B1, the selected public window must satisfy
`notBefore <= start < end <= credentialExpiry`, `start <= now < end`, and
`end - start <= maxTTL`. A proof may use a shorter window near credential expiry;
the independent witness check accepted this boundary case. Cached reuse lasts only
until `end` or the next global epoch change, whichever occurs first. Common calendar
windows can reduce distinctive timestamps, but a credential activated mid-period
cannot prove a window starting before its activation. An issuer/prover must choose
a feasible shorter window or wait for the next period.

The fixture's 30-day maximum TTL and 90-day credential lifetime are synthetic
parameters, not externally validated operational policy. Longer economic horizons
must include credential renewal and root/policy refresh costs. Economic sensitivity
analysis over other periods is a scenario exercise; it does not demonstrate that
the 90-day fixture remains usable without renewal over those longer horizons.
