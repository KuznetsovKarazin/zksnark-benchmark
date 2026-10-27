# PETs4DeFi: a small signed-credential access-cost pilot

**Status: historical v1 diagnostic; use [v2](../pets4defi_access_v2/README.md) for the current comparison.** This example records the cost of adding a proof to a signed-credential gate. Its baseline already hides the raw age, while the holder and stable credential identifiers remain public, so the measurements do not establish a privacy gain. Preserve these results as the v1 reference. See [PUBLIC_INPUT_REVIEW.md](PUBLIC_INPUT_REVIEW.md) for the tested public-input binding behavior and the npm 10 lockfile repair.

This example compares two ways to authorize the **same synthetic token deposit**. It produces local transaction measurements, rejection tests and an explicit economic scenario table. It is a research prototype, not a KYC service or a production DeFi application.

| Variant | Authorization for the deposit |
| --- | --- |
| **B0 / `baseline`** | The issuer signs an eligibility bit, holder, credential ID and expiry using secp256k1/EIP-712. The gate checks that signature and eligibility. |
| **B1 / `zk`** | The issuer signs a commitment, holder, credential ID and expiry using the same signature scheme. The gate checks that signature **outside the ZK proof**, then verifies a Groth16 proof that the commitment opens to an 8-bit age of at least 18 and a salt. |

Both variants enforce the holder, expiry, revocation and sequential nonce, then transfer 100 units of the 18-decimal **Mock Test EUR** token. The token has no monetary value. The same `AccessGate` contract is deployed in two modes. There is no withdrawal function.

This adds a compact example to the original framework. The original large `ecdsa_verify.circom` circuit is deliberately unchanged. The example has its own scripts and pinned dependencies and does **not** use the legacy benchmark runner or its verification-output parser. It checks the strict Boolean returned by `snarkjs.groth16.verify` and the deployed verifier.

## Run locally

Requirements: Node.js 20 or later, npm, Python 3, and an installed Git checkout. No wallet, real funds, external RPC service, globally installed Circom, or Python packages are required.

From the repository root:

```sh
cd examples/pets4defi_access
npm ci && npm run demo
```

The command compiles the circuit, creates a local demonstration setup, runs the comparison and rejection checks on an in-memory chain, exports the economic tables, and runs the economic-model unit tests. First execution includes setup; subsequent executions reuse a matching local setup after checking hashes of the circuit, dependency lock, proving key, WASM, Solidity verifier and verification key. Each benchmark starts a fresh chain. Generated files under `build/` and `results/` are local outputs; repeat runs replace the measurement and scenario files. Keep an external copy of any annotated price table before rerunning.

Individual stages are `npm run setup`, `npm run benchmark`, `npm run economics` and `npm run test:economics`.

## Read the outputs

| Output | What it establishes |
| --- | --- |
| `results/measurements.json` | Measured event gas and proof timings, execution environment, source hashes and setup provenance. |
| `results/test_results.json` | Passed checks, expected rejection reasons, failed-transaction gas where measured, and unchanged state after rejection. |
| `results/transactions.json` | Local transaction receipts, including successful and reverted transactions. |
| `results/event_measurements.csv` | Per-event means, ranges, sample counts, units and transaction references. |
| `results/scenario_results.csv` | 270 conditional economic scenarios derived from those measurements. |
| `results/price_inputs.csv` | Blank issuer-issuance, refresh and ETH/EUR inputs with explicit unknown status. Filling this file does not automatically reprice the model. |
| `results/proofs/`, `results/fixtures.json` | Synthetic proof examples and deliberately public demonstration data. |
| `build/setup.json` | Circuit/dependency hashes and the local setup's status. |

A completed run must finish successfully and report zero failed benchmark checks. The negative cases include replay, the wrong holder or issuer, malformed signatures, changed signature domains, expiry and revocation, incorrect proof context, corrupted proofs, underage inputs and incorrect commitment openings. Check the actual test report rather than treating the mere existence of output files as a passed run.

## What is public, and what the proof does

The circuit's private witness is `age` and `salt`. Its public signals, in exact order, are:

```text
[actionBinding, commitment, requestHash]
commitment    = Poseidon(age, salt)
actionBinding = Poseidon(salt, requestHash)
```

The contract independently computes the request hash from the chain, gate address, holder, token, amount, nonce, credential ID and expiry. It checks that hash and the signed commitment against the proof's public signals. The issuer signature authenticates the commitment; the proof checks its opening and eligibility. The gate separately handles expiry, revocation and nonce consumption. A failed transaction rolls back token and deposit state.

EIP-712 signatures are bound to a particular chain and gate address. The demonstrated credential reuse is **within one application**. Reuse in another application needs another issuer attestation or a redesigned trust/domain model; cross-application reuse is not implemented.

The holder address, stable commitment, credential ID, expiry, amount and transactions remain public and linkable. The fixtures deliberately publish the example age, salt and deterministic local keys: **this run does not protect anyone's personal information**. B0 already exposes only a signed eligibility bit, not a raw age. B1 therefore has no automatic privacy advantage over this baseline; its additional cost must be interpreted alongside a clearly specified functional or privacy goal.

## Measurement boundary

- Gas is measured on **Ganache with the Shanghai EVM rules**, Solidity compilation targeting Shanghai, chain ID 31337. These are local execution measurements, not current Ethereum mainnet measurements or fee quotations.
- There is one first deposit and five sequential repeat deposits **per variant**, using the same holder and gate: six successful actions per variant. Each B1 action has a fresh proof. This small pilot is not a population estimate or a latency service-level claim.
- An unlimited token approval is made once per gate. Each gate's shared token balance is preseeded with one token base unit, recorded separately as shared setup, so the first measured deposit represents a **new holder at an initialized service**, not the service's first-ever receipt. Repeat deposits retain allowance, balances and deposit state. Other token, allowance or account-state choices need new measurements.
- Proof timing covers `fullProve`: file reads, witness generation and proving. Off-chain proof verification is timed separately. The economic scenarios use the sample-weighted mean across all six successful proofs for both cohorts: process cold/warm state is independent of whether a user is new or returning. Network, issuer-service, wallet and user latency are excluded.
- Deposit receipt gas already includes calldata, gate checks, proof verification where applicable, and token transfer. **Do not add verifier gas a second time.** Deployment, approval and revocation appear as separate measured events.

The Groth16 setup is generated by one local process for demonstration. It is not a production trusted setup or an independent multiparty ceremony. The code and circuits have not undergone a production security audit. Use only synthetic inputs and local test assets.

## Economic scenario boundary

The exporter creates **270 rows = 2 cohorts × 3 workloads × 5 user-cost shares × 3 assumed gas prices × 3 credential validities**. Each row contains both B0 and B1.

| Dimension | Values / assumption |
| --- | --- |
| Horizon and workload | 90 days; 1, 10 or 100 accesses at times `90*i/n`, for `i=0,...,n-1`. |
| Cohort | New: issue at day zero, one approval and one first deposit. Returning: historical issuance/approval are sunk; existing gate state and allowance are assumed. |
| Credential validity | 30, 90 or 365 days; returning users start with half that period remaining. These are model assumptions, not compliance recommendations. |
| Refresh | Refresh on the first use at or after expiry, then set expiry to that use time plus the validity period. No refresh is charged merely because time passes without use. |
| Gas price | 1, 10 or 100 gwei as illustrative effective prices, **not observed market percentiles**. |
| B1 user share `alpha` | 0, 0.25, 0.5, 0.75 or 1. B0 user pays the full modeled chain cost. B1 remainder is allocated to the service. |

The B1 share is an **economic allocation assumption**: the contracts do not implement a relayer, reimbursement or gas sponsorship. In the actual transactions, the submitting holder pays gas. Changing `alpha` reallocates costs; it does not reduce total resource use. The extra service-fee assumption is fixed at zero, and no revenue or adoption model is implemented.

The exporter prices successful access and required initial approval gas in ETH. It reports B0, B1 and their difference. Returning users' historical issuance is excluded from prospective cost; refreshes within the horizon are retained. Refresh is modeled as an off-chain issuer event with **unknown price**, not as a new on-chain transaction or an assumed complete repeat of KYC. The benchmark itself uses one 90-day credential; other validity scenarios extrapolate event counts rather than measuring issuer operations.

Shared deployment/setup costs are excluded from per-user scenario totals. Measured revocation and failure gas are available separately; no revocation or failure frequency is assumed in the grid. Issuer prices, proving-service prices, other operating costs and ETH/EUR conversion remain unknown. A blank price is not zero. The outputs are conditional access-cost estimates, **not full service costs, expected profits, equilibrium fees or predicted adoption**.

See [HANDOFF.md](HANDOFF.md) for Nataliya's next three steps.
