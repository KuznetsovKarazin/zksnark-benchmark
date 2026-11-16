# Internal validation record

16 November 2026. Python 3.12.14. This is an internal reproduction, not an
independent external review, new EVM measurement or scientific novelty decision.

`python3 reproduce.py` completed with exit status 0:

* 34 unit tests passed.
* 73 source files verified; 54 archived scenarios and 8,832 access decisions
  replayed with zero discrepancies.
* 576 small schedules agreed with exhaustive optimality enumeration.
* 84 feasible hidden-coin transcripts agreed with an independent latent-coin
  enumeration; total probability checks passed. Existing 172 transcript and
  15,472 accepting-set checks were retained.
* All 78,168 modeled grid runs completed. These runs are parameter/seed cases,
  not independent real-world deployment observations.
* All 26 result files were regenerated in a temporary directory and matched the
  bundled files byte for byte.
* The two handoff CSVs were regenerated and matched byte for byte. Nine actor
  comparisons balance transfers and resource totals; there are 72 actor rows.
* Four figures and all six pages of the Russian review were visually inspected.
  Local Markdown links resolve within the standalone package.

See [reproduction log](REPRODUCTION_LOG.txt), [numeric validation](results/validation.json)
and [provenance](PROVENANCE.json). The reproduction log records the 134-file
manifest present at execution. This record and that log were added afterward;
the final SHA256SUMS was regenerated and every entry rechecked before packaging.
Only documentation was added after the successful numerical reproduction.

The repository workflow runs the same reproduction command on Python 3.12.
Cross-version byte identity of numerical results has not been established for
other Python releases. Python 3.10+ can execute the code; use 3.12 for the recorded
reproduction. Rendered document and figure bytes depend on fonts and libraries.

The remaining limits are in [MODEL.md](MODEL.md) and the
[conditional statements](proofs/CONDITIONAL_RESULTS.md). In particular, high cover
probabilities defeating the supplied clustering baseline do not prove security
against stronger attackers, and no attack against the EF design is demonstrated.
