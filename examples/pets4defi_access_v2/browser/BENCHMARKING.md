# Browser and physical-device measurements

This harness runs the real snarkjs **0.7.6 Groth16** browser bundle against the synthetic access-v2 circuit. It is a local demonstration, not a production service or a benchmark of a deployed blockchain. Do not replace the supplied fixtures with credentials, personal data, or real wallet secrets.

## Current evidence

The HTML/worker/server scripts pass syntax checks, and the server's allowlisted routes were checked over HTTP, including traversal rejection and unsupported-method rejection. The available cloud browser could not reach the local server, and the connected-browser extension was unavailable. **No actual browser or physical-phone samples were obtained during this implementation check.** Node.js results, browser-shaped user agents, and simulated mobile viewports must not be presented as measured phone performance.

## Run on a computer

From `examples/pets4defi_access_v2`, install the locked dependencies and generate the synthetic assets:

```sh
npm ci
npm run setup
npm run benchmark
npm run browser
```

The server defaults to `http://127.0.0.1:8765/`. Open that address in the browser to be measured. The required files are:

| Browser URL | Local source |
| --- | --- |
| `/vendor/snarkjs.min.js` | `node_modules/snarkjs/build/snarkjs.min.js` |
| `/assets/access.wasm` | `build/access_js/access.wasm` |
| `/assets/access_final.zkey` | `build/access_final.zkey` |
| `/assets/verification_key.json` | `build/verification_key.json` |
| `/assets/browser_input.json` | `build/browser_input.json` |

`browser_input.json` must be the plain synthetic Circom input object. The server returns an explicit error for missing assets; it never substitutes fabricated timings. The server refuses to start with a snarkjs version other than 0.7.6.

Click **Start 30 cold + 30 warm runs**, keep the tab visible, and wait for the complete status. Click **Download JSON results**. Retain the raw JSON alongside the build/setup manifest and relevant dependency lockfile so later runs can be matched to the same circuit and proving key. The page does not upload or persist results automatically.

## Run on a physical phone

1. Use the same generated assets, and place the server computer and phone on a trusted local network. Start the narrowly scoped demo server with:

   ```sh
   HOST=0.0.0.0 PORT=8765 npm run browser
   ```

2. On the physical phone, open `http://<server-computer-LAN-address>:8765/` in the actual browser to be measured. Use the computer's real LAN address, not the phone's `localhost`. Allow the selected port through the local firewall only if required for this test. Do not expose this demo server to the public internet.
3. Record the phone model, operating-system and browser versions, power/charging state, and whether power-saving mode was active in the experiment notes. These details are not guessed by the harness. Keep the tab in the foreground, prevent screen lock for the run, avoid other heavy work, and keep the same power policy when comparing runs. Thermal state can affect results, so document it when known.
4. Run the same button-driven protocol and save that phone's own JSON export. Repeat on each device/browser being compared; do not reuse desktop samples as mobile measurements.
5. Stop the server with Ctrl-C after testing.

Binding `HOST=0.0.0.0` exposes only the explicit route allowlist, including the synthetic input and proving assets, to reachable network peers. It does not serve arbitrary files. Plain HTTP on a LAN address may not expose Web Crypto's secure-context hashing API or every browser metadata field. Missing SHA-256 hashes and device-memory values are recorded as `null`, not invented. In that case retain and identify the server-side setup/build manifest; do not claim that the export itself cryptographically identified every downloaded asset.

## Protocol and interpretation

- **Cold:** 30 sequential samples, each using a newly created dedicated worker. This resets that worker's JavaScript context. It does **not** flush browser compilation caches, the operating-system cache, or CPU caches; it is not a freshly booted-device or empty-cache measurement.
- **Warm:** a separate dedicated worker performs one verified warm-up, which is retained in the JSON but excluded from all summary statistics. The same worker then performs 30 measured calls. Asset bytes and the worker runtime are retained. Each call still runs the complete `fullProve` API, including its witness calculation; this is not a proof-only loop or a precomputed-witness benchmark.
- **Verification:** every measured proof and the warm-up must return exactly `true` from `snarkjs.groth16.verify`. A verification failure, worker failure, changed asset identity, or per-run timeout aborts the session. Partial exports are labelled `failed` or `cancelled` and must not be reported as a completed 30 + 30 experiment.
- **Threading:** `fullProve` receives `{ singleThread: true }` as its sixth argument. snarkjs 0.7.6's `verify` does not expose a matching argument. The harness disables nested `Worker` construction inside the dedicated worker, activating ffjavascript's browser single-thread fallback. This is an explicit reproducibility choice, not the default maximum-throughput browser configuration.
- **fullProve milliseconds:** witness calculation plus proof generation after the library and synthetic assets are loaded. Asset download and hashing are excluded.
- **Off-chain verification milliseconds:** the complete verification API call. It is not smart-contract gas, transaction inclusion latency, RPC latency, or on-chain execution time.
- **Worker wall milliseconds:** measured by the page from before worker creation for each cold sample and the excluded warm-up, or just before the request to the reused worker for warm samples, until the result message arrives. Cold worker wall time includes initialization, asset loading/hashing, computation, and messaging. It does not include the subsequent UI rendering or the next run's worker teardown.
- **Summary:** report `n`, median, Q1, Q3, IQR, minimum, and maximum for each metric and phase. Quartiles use linear interpolation at `(n - 1) × p`, and `IQR = Q3 - Q1`. The export retains unrounded millisecond samples; the table displays two decimal places. Do not pool cold and warm samples.
- **Environment:** user agent, reported hardware concurrency, and device memory when available describe only the browser making the measurements. These reported values are not independently verified hardware specifications. Visibility transitions and each sample's start/end visibility are retained; flag backgrounded or interrupted sessions when interpreting the timings.

Record whether a dataset came from a local desktop browser, a cloud desktop browser, or a physical phone. Preserve separate exports and describe the actual execution environment in any report.
