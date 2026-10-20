# Threat model and claim boundaries

This is a synthetic access-control experiment for an Ethereum-compatible DeFi deposit gate. It is neither a KYC service nor a demonstration of legal compliance. All names, secrets, credentials, jurisdictions and tokens in the fixtures are public test data.

## What is compared

| Property | Signed direct / cached | ZK direct / cached |
|---|---|---|
| Eligibility | Trusted issuer signs a policy-versioned eligibility bit | Proves active credential membership, tier threshold, allowed-jurisdiction membership and validity window |
| Raw attributes on chain | Not disclosed | Not disclosed |
| Issuer identity at presentation | Recoverable from signature | Hidden among active issuer slots, subject to anonymity-set and metadata limitations |
| Credential identifier | Public signed ID | Private leaf and path; no public credential ID or holder commitment |
| Application identifier | Registry-wide EIP-712 credential, reusable across gates | Application scope derived from chain, gate and policy ID |
| Presentation identifier | Holder wallet and signed credential ID | Scope-specific pseudonym; stable within one gate |
| Issuer contacted to authorize each use | No | No, **if current witness data is obtainable independently** |
| Wallet and token flows | Public | Public |
| Cache validation | Current global registry epoch and expiry | Same rule |

The fair signed baseline is already reusable. Neither reusable credentials nor hiding a raw attribute is presented as an exclusive ZK advantage. The measured ZK improvement is hiding the issuer and credential-level cross-application identifier while proving predicates locally. No proof of full-system anonymity is claimed.

## Adversaries and assumptions

**Public observer.** Sees transactions, sender, token movements, authorization windows, scope pseudonyms, global roots and issuer root-update transactions. It cannot extract the hidden attribute/issuer/path from a sound zero-knowledge proof. Reusing a wallet, funding fresh wallets from a common source, timing, rare policy combinations, or a small anonymity set can still link users.

**Issuer.** Knows the attributes it checked and the commitment it issued. In a real issuance protocol the holder must generate and retain `secret`; the issuer receives the holder commitment, not that secret. This repository implements the proof and authenticated root interface, **not a privacy-preserving issuance or witness distribution service**. The synthetic fixture generator necessarily knows all test secrets. An issuer that learns the secret can compute scope pseudonyms. A malicious issuer can also issue false attributes or watermark validity/root updates; this construction trusts issuers' factual assertions and does not prove honest KYC.

**Colluding applications.** Cannot match the credential-level pseudonyms solely by equality across distinct scopes under the cryptographic assumptions. They can correlate public wallets and off-chain metadata. Fresh independently funded wallets and a suitable transport/relayer are prerequisites for a stronger operational unlinkability claim; neither is delivered by a nullifier alone.

**Malicious holder.** May change amounts, sender, token, nonce, scope, expiry, public inputs, witnesses and roots, replay a proof, or share a secret. The gate binds a proof to chain/gate/sender/token/amount/nonce/registry epoch/window and checks the current roots. The per-scope pseudonym is bound to the first wallet for that scope; sharing a secret before first use is not prevented. This is a reusable pseudonym, not a one-use voting nullifier.

**Registry owner and issuer keys.** Registry owner chooses trusted issuers and policy. An issuer can update only its own root; removal by the owner is permanent in this pilot. Compromised trusted keys can issue/revoke or deny access. Trust is explicit and is not removed by ZK.

## Status, expiry and cache semantics

- Hidden credentials are leaves of an **active-set** Merkle tree. Removal makes a newly generated proof impossible for that leaf against the current root. This is active-set membership, not a sparse-Merkle non-membership/status-list implementation.
- Public signed IDs use a separate issuer-scoped revocation mapping. `revokePublic(id)` alone does **not** remove a hidden leaf. The synthetic comparison must perform the relevant operation for each representation; a production issuer service must coordinate them where they represent the same underlying credential.
- Every root update, policy change, issuer removal or public revocation increments one global epoch. All cached authorizations become stale immediately. This deliberately conservative rule avoids silently granting access after a status change, but creates a real economic cost when unrelated credentials change frequently.
- Public proof window satisfies `notBefore <= windowStart <= now < windowEnd <= credentialExpiry`, with window length at most `maxTTL`. The signed cache expires at `min(credential expiry, authorization time + maxTTL)`. The economic trace treats validity and cache TTL separately.
- Windows are public metadata. Deployments should standardize windows and policy cohorts rather than exposing distinctive issuance/expiry patterns. This pilot does not implement or prove metadata-resistant scheduling.
- Proofs need current tree paths. Publishing a new root alone is insufficient for offline reuse. A broadcast/public witness-update distribution service and its bandwidth/availability costs remain unmeasured. An issuer queried per use could observe use timing and defeat the intended privacy benefit.

## Capacity and setup

The circuit has credential depth 10, issuer depth 2 and policy depth 3: at most 1,024 active leaves per issuer, four issuer slots and eight allowed jurisdiction leaves. The fixture populates eight credentials; population cost allocation is a scenario, not a 1,000-user load test. Changing depths changes proving cost and requires new circuit-specific setup.

Phase 1 uses a published, hash-pinned Powers of Tau transcript. Phase 2 has two contributions generated by one local process. They are **not independent participants** and do not establish a production-safe ceremony. The generated keys must never be used to protect funds.

## Explicitly outside the measured result

No production lending logic, sanctions screening, legally validated policy, GDPR liability valuation, ERC-4337 paymaster, EIP-7702 sponsorship, proof aggregation, identity recovery, anonymous transport, mobile wallet integration, or P-256/EdDSA signature-in-circuit implementation is claimed. Token accounting assumes the supplied exact-transfer token; fee-on-transfer, rebasing and dishonest tokens are unsupported. Static analysis and adversarial tests are useful evidence, not a security audit.
