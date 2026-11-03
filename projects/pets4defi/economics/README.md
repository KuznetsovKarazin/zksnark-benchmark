# Economic reproduction for private eligibility access

**Research author: Nataliya Kolyada. Technical input owner and scientific reviewer:
Oleksandr Kuznetsov.**

The computational core from Nataliya's accepted ECON-05 v0.3 package is integrated
here without changing its source bytes. It was supplied inside ECON-06 v0.3.
[SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) records both archive checksums and
the source path and SHA-256 of all 26 included files. The original archives remain
unchanged. The nested README is historical source documentation; its old review
status is not the current integration status.

Run from the repository root, with Python 3.10 or later and no extra dependencies:

```sh
python3 projects/pets4defi/economics/reproduce.py
```

This checks source integrity, executes the model and independent central-result
calculation in a temporary directory, runs 39 tests, and requires byte-identical
regeneration of four numeric CSVs. It does not modify the retained inputs or
results. The workbook, workbook builder, prose report and old figures were not
imported: none is required for numeric reproduction. The optional original
`make_figures.py` uses matplotlib.

The core has 15 modeled cases (1/10/100 deposits crossed with five user shares),
repriced at two historical fees. A separate six-row result shifts exactly two
revocations. These are not 30 physical experiments and not the complete new EVM
traces in [REVOCATION_VALIDATION.md](../REVOCATION_VALIDATION.md).

Historical gas observations and source commits remain pinned in the imported
metadata. Later EVM receipt sums must not silently replace these economic inputs.
Reimbursement is a conditional cash transfer, not an implemented refund or
paymaster. Off-chain expenses, demand, revenue and profitability remain unmeasured.
This integration is computational verification, not an independent human review.
