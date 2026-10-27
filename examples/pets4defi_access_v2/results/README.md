# Evidence package

Start with `../RESULTS.md` and `ECONOMIC_INTERPRETATION.md`.

- `raw_ci_node24.zip` is the complete, unchanged artifact of the successful Node24/npm11 run. It contains raw transaction receipts, all measured events, proof samples, the exact verifier/verification key, security checks and the original accounting output. `ci_provenance.json` records artifact SHA-256, workflow, reviewed head and tested PR merge commit. Source-file hashes match the branch source.
- `economic_tables.zip` contains all current CSVs, including large trace/price tables. Its manifest records every file hash. The current price conversions additionally use the separately timestamped fee snapshot; they do not modify transaction evidence.
- `fee_snapshot.json` and `fee_history_raw.json.gz` are a separate public-RPC observation with exact windows, metric definitions and raw responses.
- `server_prover.json` is a separate local 30-cold/30-warm measurement; `server_setup.json` identifies its setup. Its machine and key differ from the CI transaction run. Browser and phone results remain unmeasured.
- `static_analysis/` contains reviewed findings and dependency advisories, not an assertion of production security.

Run `npm run demo`, `npm run prover`, `python3 scripts/report.py`, and `python3 scripts/package_results.py` to regenerate. For a new fee window, run the bounded `scripts/collect_fees.py` separately and then re-export economics. Keep each run's source, setup and environment provenance together.
