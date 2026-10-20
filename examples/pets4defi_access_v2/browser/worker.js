'use strict';

// snarkjs 0.7.6 verify() has no singleThread parameter. Its ffjavascript
// browser runtime uses a single-thread fallback when Worker is unavailable.
// Keep this dedicated worker, but explicitly disable nested workers so both
// proof generation and verification have a reproducible single-thread policy.
self.Worker = undefined;

let statePromise;
let busy = false;
const assetPaths = {
  wasm: '/assets/access.wasm',
  zkey: '/assets/access_final.zkey',
  verificationKey: '/assets/verification_key.json',
  input: '/assets/browser_input.json',
};

async function loadAsset(path) {
  const response = await fetch(path, { cache: 'no-store', credentials: 'omit' });
  if (!response.ok) throw new Error(`Could not load ${path}: HTTP ${response.status}. Run setup first.`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  let sha256 = null;
  if (self.crypto?.subtle) {
    const digest = new Uint8Array(await self.crypto.subtle.digest('SHA-256', bytes));
    sha256 = Array.from(digest, (value) => value.toString(16).padStart(2, '0')).join('');
  }
  return { bytes, metadata: { path, bytes: bytes.byteLength, sha256 } };
}

async function initialize() {
  const started = performance.now();
  const libraryStarted = performance.now();
  importScripts('/vendor/snarkjs.min.js');
  const libraryLoadMs = performance.now() - libraryStarted;
  if (typeof snarkjs?.groth16?.fullProve !== 'function' || typeof snarkjs?.groth16?.verify !== 'function') {
    throw new Error('The snarkjs Groth16 browser API is unavailable.');
  }
  const assetStarted = performance.now();
  const entries = await Promise.all(Object.entries(assetPaths).map(async ([name, path]) => [name, await loadAsset(path)]));
  const loaded = Object.fromEntries(entries);
  const decodeJSON = (asset) => JSON.parse(new TextDecoder().decode(asset.bytes));
  const verificationKey = decodeJSON(loaded.verificationKey);
  const input = decodeJSON(loaded.input);
  if (!input || Array.isArray(input) || typeof input !== 'object') throw new Error('The synthetic input must be a Circom input object.');
  if (verificationKey.protocol !== 'groth16' || !Number.isInteger(verificationKey.nPublic)) {
    throw new Error('Expected a Groth16 verification key with an integer nPublic.');
  }
  return {
    wasm: loaded.wasm.bytes,
    zkey: loaded.zkey.bytes,
    verificationKey,
    input,
    assets: Object.fromEntries(entries.map(([name, asset]) => [name, asset.metadata])),
    initialization: {
      libraryLoadMs,
      assetLoadAndHashMs: performance.now() - assetStarted,
      totalMs: performance.now() - started,
    },
  };
}

self.onmessage = async (event) => {
  const { type, requestId } = event.data ?? {};
  if (type !== 'run' || !Number.isInteger(requestId)) return;
  if (busy) {
    self.postMessage({ type: 'error', requestId, error: 'This worker already has an active run.' });
    return;
  }
  busy = true;
  try {
    const firstRunInWorker = !statePromise;
    if (!statePromise) statePromise = initialize();
    const state = await statePromise;
    const proveStarted = performance.now();
    const { proof, publicSignals } = await snarkjs.groth16.fullProve(
      state.input,
      state.wasm,
      state.zkey,
      undefined,
      undefined,
      { singleThread: true },
    );
    const fullProveMs = performance.now() - proveStarted;
    if (!Array.isArray(publicSignals) || publicSignals.length !== state.verificationKey.nPublic) {
      throw new Error('Generated public-signal count does not match the verification key.');
    }
    const verifyStarted = performance.now();
    const verified = await snarkjs.groth16.verify(state.verificationKey, publicSignals, proof);
    const offchainVerifyMs = performance.now() - verifyStarted;
    if (verified !== true) throw new Error('Strict Groth16 verification failed; sample rejected.');
    self.postMessage({
      type: 'result',
      requestId,
      result: {
        fullProveMs,
        offchainVerifyMs,
        proveAndVerifyMs: fullProveMs + offchainVerifyMs,
        verified: true,
        publicSignalCount: publicSignals.length,
        firstRunInWorker,
        initialization: firstRunInWorker ? state.initialization : null,
        assets: state.assets,
      },
    });
  } catch (error) {
    self.postMessage({ type: 'error', requestId, error: error instanceof Error ? error.message : String(error) });
  } finally {
    busy = false;
  }
};
