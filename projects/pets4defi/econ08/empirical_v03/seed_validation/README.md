# Independent repetitions on synthetic schedules

The validation design fixes ten new seeds (30001 through 30010), four and 64 issuers, 90 days, activity 0.45 and independent label flips and missing observations at 10% each. No real accounts, user traces or network calls are used. These statistics supplement the original 20-seed HMM grid and the published shared-epoch controls.

For each size and seed, the existing HMM scores the same 128 simulated paths twice: once using the generating rates and once using rates estimated from a separate 1,000-event calibration sample with half-count smoothing. The paired difference is estimated minus known accuracy, in fractions. A separate generated panel of 10,000 holders reproduces the original clustering settings. ARI scores the full partition; anchored accuracy scores all 9,000 undisclosed holders, treating abstention as incorrect. A permuted-assignment ARI is a negative scoring control. Each size, seed and panel has its own random stream. No seeds are shared with the published single positive run. The standard deviation and two-sided Student-t 95% interval half-width use independent seed estimates; they do not describe variation between real sources.

Run from a checkout with the adjacent src/ directory present:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python run.py --workers 2

Outputs are seed-level aggregate metrics in seeds.csv and their summaries in summary.csv. No membership assignments or individual paths are written.
