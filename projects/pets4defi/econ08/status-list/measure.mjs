import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
import {availableParallelism, cpus, platform} from 'node:os';
import {performance} from 'node:perf_hooks';
import {fixture, START} from './fixture.mjs';
import {LIST_BYTES, encodeList, expandList, statusVerifier, verifyList} from './status.mjs';

const [session, out] = process.argv.slice(2);
assert(['1', '2', '3'].includes(session) && out, 'Usage: node measure.mjs SESSION OUTPUT.json');
const f = await fixture();
const revoked = Array.from({length: 12}, (_, i) => i * 997 + 7);
const payload = f.document({revoked});
const signed = await f.sign(payload);
const raw = JSON.stringify(signed);
const entry = f.entry(7);
const newVerifier = () => statusVerifier({trust: f.trust, clock: () => START, maxAgeMs: 120_000,
  retrieve: async () => JSON.parse(raw)});
const warmVerifier = newVerifier();
await warmVerifier(entry);
const operations = {
  build: () => encodeList(revoked),
  sign: () => f.sign(payload),
  verify_signature: () => verifyList(signed, f.trust),
  expand: () => expandList(payload.credentialSubject.encodedList),
  cold_verifier_lookup: async () => assert((await newVerifier()(entry)).revoked),
  cached_lookup_batch: async () => {for (let i = 0; i < 1000; i++) assert((await warmVerifier(entry)).revoked);},
};
const samples = {};
for (const [name, operation] of Object.entries(operations)) {
  const observations = [];
  for (let i = 0; i < 11; i++) {
    const start = performance.now();
    await operation();
    observations.push(performance.now() - start);
  }
  samples[name] = {excluded_warmup_ms: observations[0], ms: observations.slice(1)};
}
const sizes = {};
for (const count of [0, 1, 12, 512]) {
  const doc = f.document({revoked: Array.from({length: count}, (_, i) => i * 173 + 7)});
  const encoded = doc.credentialSubject.encodedList;
  sizes[count] = {uncompressed_bytes: LIST_BYTES, gzip_bytes: Buffer.from(encoded.slice(1), 'base64url').length,
    encoded_chars: encoded.length, signed_json_bytes: Buffer.byteLength(JSON.stringify(await f.sign(doc)))};
}
writeFileSync(out, JSON.stringify({session: Number(session), node: process.version, platform: platform(),
  cpu: cpus()[0]?.model, parallelism: availableParallelism(), cached_lookup_batch_size: 1000,
  network: 'in-process fixture JSON, excludes HTTP', timings_fixture_revoked_count: 12, sizes, samples}, null, 2) + '\n', {flag: 'wx'});
