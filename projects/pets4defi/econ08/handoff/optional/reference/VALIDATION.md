> Optional evidence note. Original source paths and rerun commands are retained as provenance; executing them needs the separate source repository. Nataliya does not need to run them.

# ECON-08 restored evidence validation — 13 November 2026

The historical pilot and cohort data are preserved byte-for-byte. The source
bundle retains five previously unpublished commits above public base
`53f47c383a96e86641b6a18fb98636f7ab9b5da4`. Pilot source is
`012044c17d4dc98ca6eae8f696e04252f9fb0d5a`; cohort source is
`df4352cfc6cf11fd810ee1d7a868f6c6752bbbe1`; bundle head is
`2d3096743d483c662696167bbc1cc2383a9bef67`.

## Audit changes

The old audit matched proof indices, nonces and timestamps, but did not compare
the saved proof coordinates with transaction calldata. The restored audit now
reconstructs the static `PolicyGate.depositZK` ABI payload independently in
Python, including the Solidity order of the Fq2 coordinates, all eight public
signals and successful action arguments. It covers every saved proof, including
proofs used by deliberately rejected diagnostic calls. A separate ethers check
reconstructs each signed transaction and checks its hash, sender and destination
against the saved receipt. The snarkjs check verifies the proof equations.

Five new corruption cases reject changed proof coordinates, public inputs,
calldata, proof links and method selectors even after the archive manifest is
rehashed. Two JavaScript checks cover the original signed transaction and
changed calldata with unchanged transaction-hash metadata.

`audit_archive.py` also verifies the original source hashes directly against the
recorded Git commits, reconciles all cohort CSV gas totals, and checks the
separate pilot timing/figure manifest. New helper files are included in future
runner source manifests; original measurements retain their original manifests.

## Reproduce the saved-evidence checks

From the repository root, import the original source objects, then run:

```sh
git bundle verify projects/pets4defi/econ08/ECON08_source.bundle
git fetch projects/pets4defi/econ08/ECON08_source.bundle refs/heads/econ08-cohort
cd examples/pets4defi_access_v2
npm ci --ignore-scripts
python3 scripts/econ08/audit_archive.py
node --test scripts/econ08/test_config.mjs scripts/econ08/test_transactions.mjs
python3 -m unittest discover -s scripts/econ08 -p 'test_check.py' -v
node scripts/econ08/verify_proofs.mjs --expected-proofs 512 results/econ08_native_pilot results/econ08_cohort/runs/*
```

Expected archive quantities are 32 pilot scenarios / 1,616 normal accesses and
22 cohort scenarios / 7,216 normal accesses. The 512 proofs comprise 87 pilot
proofs, 33 pilot timing proofs (30 measured and three warm-ups), and 392 cohort
proofs. Timing proofs are not on-chain transactions. The model/signature tests
contain seven cases; the Python evidence-corruption suite contains ten cases.

Local revalidation on 13 November 2026 passed all 54 archived scenarios, all
512 proofs, all 10,627 signed transaction reconstructions, 18 public-input
tampering controls, seven JavaScript tests, and ten Python tests. This is a new
audit of preserved evidence, not a new measurement campaign.

The dedicated workflow audits these saved measurements and the status-list
component without regenerating the proving setup or executing new workloads.
No fresh EVM measurements were generated during this restoration. Independent
technical peer reproduction remains open.
These checks establish internal reproducibility and evidence consistency. They
do not establish production security, public-chain finality, independent
workload replication, or device/population latency variation.
