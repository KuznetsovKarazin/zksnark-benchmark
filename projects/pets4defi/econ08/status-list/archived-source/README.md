# ECON-08 authenticated status-list component

This local experiment measures a single-issuer, single-purpose revocation list for an already authenticated status entry. It uses the [W3C Bitstring Status List v1.0 Recommendation](https://www.w3.org/TR/2025/REC-vc-bitstring-status-list-20250515/) §§2.1–2.2, 3.1–3.4 and 7.1 for the list format and [EdDSA Data Integrity v1.0](https://www.w3.org/TR/vc-di-eddsa/) §3.3 for `eddsa-jcs-2022`. The package uses a pinned issuer key and an offline document loader. It accepts the experiment's fixed 16,384-byte list, one-bit revocation status, and UTC timestamps.

The status signature covers the encoded list, publication timestamp, expiry and refresh TTL. The verifier checks the configured issuer, key and URL. It uses an exclusive age limit from signed publication and enforces signed expiry. A fetch of the same version does not restart its age. A previously accepted publication cannot be replaced in the same process by an older signed list or a different list bearing the same timestamp. An unavailable source permits cache reuse only until the signed validity or configured maximum age is reached. Bad signatures and invalid responses produce errors.

The lab uses a 60-second refresh TTL, 120-second maximum age, synchronized synthetic clocks and local JSON retrieval. The replay check keeps state in memory. External issuer decision-to-publication lag, HTTP transport, clock-skew tolerance, durable rollback protection, original credential verification, EVM integration and unlinkable presentation are outside this component boundary. A production freshness bound needs explicit values for the missing stages.

## Reproduce

From this directory with Node.js 24:

```sh
npm ci
node --test status.test.mjs
mkdir -p /tmp/econ08-status-measurements
for session in 1 2 3; do
  node measure.mjs "$session" "/tmp/econ08-status-measurements/session_${session}.json"
done
```

Use a fresh output directory. The benchmark uses 10 observations after one excluded warm-up per operation in each of three sequential fresh Node processes. Each cached-lookup sample is a batch of 1,000 calls. The cold-verifier lookup creates a new cache and includes local JSON parsing, signature verification, list expansion and a lookup. It uses a process that has already loaded the libraries. Sizes are serialized bytes for the synthetic fixture, with no HTTP headers or transport. Results are process-local wall-clock times from a single host. The signed document size depends on the key identifier and proof representation as well as the list contents.

`session_*.json` in the measurement archive contains the raw observations. `summary.csv` reports medians and empirical nearest-rank p95 for 30 timed samples per operation. The size entries summarize three signed fixtures per density. The 131,072-bit capacity is fixed. The revoked counts and generated positions are fixture inputs. No EVM gas or end-to-end economic cost is reported for this component.
