# Issuer observability pilot v0.2

16 November 2026. Research results, reproducible code and the next economic task.

**Result:** common invalidation is authorization-count optimal within the stated
observable-cache architecture. One coin per foreign publication gives a measurable
cost/information tradeoff, but no finite pure-epsilon guarantee for rho<1. Anonymous
publication timestamps can support cohort clustering in this modeled application;
coverage and false attribution matter. No attack against Ethereum Foundation is
demonstrated. Independent assessment of scientific novelty remains open.

## Start here

* English review: [PDF](ECON08_Observability_Review_EN_v0_2.pdf) / [DOCX](ECON08_Observability_Review_EN_v0_2.docx) — six-page results and assessment.
* [Nataliya's revised task](handoff/START_HERE.md) — one short economic note and a supplied payment table.
* [Conditional statements and proofs](proofs/CONDITIONAL_RESULTS.md).
* [Model and scope](MODEL.md) and [related work](review/RELATED_WORK.md).
* [Validation record](VALIDATION.md), [numeric checks](results/validation.json) and [changes from v0.1](CHANGES.md).

No new EVM run, contract, paymaster or deployment security claim is included. The
new-policy gas figures use archived coefficients and are access-only proxies.
The source snapshot is ca1fabbb1d2fb777adca87544e689a14f6b5fbdb, independent of the
later publication commit. All 73 source-file Git blob hashes and the original
report/access SHA-256 manifests are verified by the runner.

## Reproduce

From this folder after cloning or extracting the standalone ZIP:

```sh
python3 reproduce.py
```

Use Python 3.12 for the recorded byte-exact reproduction; the code requires only
the Python standard library and can run on Python 3.10+. The command checks the package hashes,
runs 38 unit tests, replays all 54 archived scenarios, reruns every modeled grid and
exact check in a temporary directory, then compares every result file byte for
byte. It also regenerates and compares the two small handoff CSVs. It does not overwrite the published results. Runtime varies by CPU; allow
several minutes. No credentials or network access are needed for reproduction.

Optional figure/document regeneration needs matplotlib and python-docx:

```sh
python3 src/make_figures.py
python3 src/build_review.py
```

Numeric byte identity is checked; document/figure byte identity is not promised
across fonts/renderers. Any regenerated document should be rendered and reviewed.

## Results guide

| File | Meaning |
|---|---|
| source_replay.csv | 54 existing scenarios and 8,832 exactly matched access decisions |
| timing_workload_runs.csv | All modeled alternatives on 12 deduplicated archive schedules |
| synthetic_timing_runs.csv | Poisson/update and access sensitivity, including delta up to 14 days |
| weekly_one_coin_exact.csv | Exact weekly expectations at 21 rho values, independently enumerated |
| extension_checks.json | 576 small optimality cases, exact hidden-coin inference and price counterexample |
| clustering_runs.csv | Anonymous 16/32/64-holder experiments, pair and external-anchor metrics |
| clustering_controls.json | No-information controls and input restrictions |
| outage_summary.csv | Complete outage/freshness grid, not only one stress point |
| economic_cases.csv | Three worked economic quantity cases and four policies |
| coalition_costs.csv | All subset costs for issuer-to-holder externalities |
| compensation_reference.csv | Two budget-balanced reference allocation rules |
| paired_cost_events.csv | Signed event differences, including later credits rather than positive-only totals |

Every stochastic table includes seed-level rows. Means and sample SD are supplied;
these are synthetic scenarios, not independent deployment samples or confidence
guarantees. Singleton probability, Bayes accuracy, entropy, clustering and named
issuer identification are different metrics. Weakness of the tested clustering
algorithm is not proof against stronger adversaries.

The known economic results from ECON-07 and the ECON-08 funding addendum remain
prior work. This pilot supplies technical quantities for the next bounded task;
it does not claim that compensation removes resource costs or establishes adoption.
