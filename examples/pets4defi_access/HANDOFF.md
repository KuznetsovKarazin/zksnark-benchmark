# Handoff for Nataliya: PETs4DeFi access-cost pilot

The pilot supplies a small, checkable technical input for the economic work. It compares a conventional issuer-signed eligibility check (**B0**) with an issuer-signed commitment plus an age-eligibility proof (**B1**) for the same synthetic deposit. The issuer signature is checked outside the proof in both cases.

The original framework's large ECDSA circuit is unchanged. This example uses a compact circuit and a separate runner so that the first economic exercise can use a bounded, reproducible measurement set.

## 1. Confirm the evidence and take the event table

Start with `results/test_results.json`, `results/measurements.json` and `results/event_measurements.csv`. Confirm that the run completed with zero failed checks and retain its source hashes and execution environment. Use the CSV's event names, units, sample counts and measured values; do not copy unverified numbers from a README or substitute literature values for these measurements.

If outputs need regenerating, a technical colleague can run:

```sh
cd examples/pets4defi_access
npm ci && npm run demo
```

There are six successful deposit actions per variant: one first-holder deposit and five sequential repeats. The service's token balance is initialized separately before measurement. Gas comes from a local Shanghai EVM; timings come from the recorded machine. Treat these as pilot measurements. Deposit gas already includes verification and token transfer. Keep deployment, balance initialization, approval, revocation and failure events separate.

**Deliverable:** a short event-cost table identifying what is measured, what is assumed, and what still needs a price or a technical measurement.

## 2. Inspect the scenario grid and its assumptions

Open `results/scenario_results.csv`. Its **270 rows** combine two cohorts, three workloads, five B1 user-cost shares, three assumed gas prices and three credential-validity periods. Each row compares B0 and B1 over 90 days.

The workload is evenly scheduled. New users incur initial issuance, approval and first-access events. Returning users start with an existing allowance/state and half a validity period left; historical issuance and approval are sunk. Credentials refresh only when used at or after expiry. Refresh is an unknown-price issuer operation, not automatically a repeat of full KYC or an on-chain transaction.

Proof times are pooled across the six successful B1 proofs for both cohorts; process warmup is not a user-cohort effect. Credential reuse is within the same application: EIP-712 binds each attestation to its chain and gate, so cross-application reuse is not demonstrated.

The gas-price values are illustrative assumptions, not market observations. `alpha` allocates B1 costs between user and service; B0 remains fully user-funded. This allocation is not implemented as a relayer. It changes who pays, not the total cost. The extra service fee is fixed at zero.

Copy `results/price_inputs.csv` into your working materials and attach sources to any proposed issuer or currency-conversion inputs. The current exporter does not consume edits to that file, and rerunning it replaces the blank template. Do not replace unknowns with zero. Shared deployment/setup costs, unmodeled failure/revocation frequencies and other operating costs remain outside the per-user totals.

**Deliverable:** a short assumptions note, proposed sourced price inputs, and any justified changes to the grid. Keep the Louafi replication exercise separate from these prototype measurements.

## 3. Draft the first ECON-03 comparison

Use the measured event costs and the declared grid to show:

- B0 versus B1 chain cost and the incremental cost of B1 as workload and gas price change.
- User/service allocation as `alpha` changes, without calling a transfer of costs an efficiency gain.
- How validity and returning-user remaining life change refresh counts, retaining symbolic issuer charges until prices are supported.

Interpret the result as an access-cost comparison. B0 already hides raw age behind a signed eligibility bit. B1 still exposes a stable commitment, holder and transaction metadata, so a privacy improvement must be established for a specific threat model; it cannot be inferred from the presence of a ZK proof. The published fixtures are deliberately synthetic and public, and the setup is for a local demonstration only.

**Deliverable:** a concise ECON-03 draft with the comparison, evidence sources, assumptions, missing inputs and the next technical question. Do not infer adoption, expected profit, an optimal community fee or a complete service cost from this pilot alone.

Nataliya and the project lead do not need to write contracts, circuits or proving code to review these outputs. Their next decisions concern the research question, cost boundary and justified assumptions; implementation changes and new measurements belong with the technical team.
