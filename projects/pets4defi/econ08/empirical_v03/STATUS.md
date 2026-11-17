# Checkpoint — 17 November 2026

- Public-field extractor: PASS on 25 archived local-EVM runs, 15,346 transactions,
  8,875 successful accesses, zero classification mismatches. Negative checks
  cover poisoned private metadata, block hashes, missing events, reverted calls,
  unknown selectors and incomplete fee components.
- HMM: seven independent/unit tests passed, including complete latent-history
  enumeration and nonuniform-prior symmetry checks.
- Synthetic robustness: all 1,600 runs (80 cases x 20 seeds; 128 holders per run)
  completed. Per-run results and summaries exist. No empirical interpretation.
- EAS acquisition: incomplete. Partial Base pagination is not a population total.
  Historical RPC coverage has not passed. The empirical headline gate is UNKNOWN.
- New batched-registry EVM runs: verification in progress. Do not treat an
  intermediate deployment manifest as a passed run.
- Public testnet: not deployed; a funded disposable signer is not configured.
- An execution-environment interruption occurred during final jobs. Source files
  survived; incomplete jobs must be rerun before reporting success.

This checkpoint is intentionally incomplete. The final verification commit will
replace it with observed outcomes and artifact hashes.
