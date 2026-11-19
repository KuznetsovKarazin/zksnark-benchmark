import assert from 'node:assert/strict';
import {test} from 'node:test';
import {gzipSync} from 'node:zlib';
import {fixture, START} from './fixture.mjs';
import {LIST_BYTES, encodeList, expandList, isRevoked, statusVerifier} from './status.mjs';

test('W3C example expansion and leftmost-first boundary indices', () => {
  const sample = 'uH4sIAAAAAAAAA-3BMQEAAADCoPVPbQwfoAAAAAAAAAAAAAAAAAAAAIC3AYbSVKsAQAAA';
  assert.deepEqual(expandList(sample), Buffer.alloc(LIST_BYTES));
  const bytes = expandList(encodeList([0, 7, 8, 131071]));
  assert.equal(bytes[0], 0x81);
  assert.equal(bytes[1], 0x80);
  assert.equal(bytes.at(-1), 1);
  assert.equal(isRevoked(bytes, 6), false);
  assert.equal(isRevoked(bytes, 131071), true);
  assert.throws(() => isRevoked(bytes, 131072), /STATUS_INDEX/);
  for (const length of [LIST_BYTES - 1, LIST_BYTES + 1]) {
    assert.throws(() => expandList(`u${gzipSync(Buffer.alloc(length)).toString('base64url')}`), /STATUS_(LENGTH|ENCODING)/);
  }
});

test('signed initial list, shared cache and published revocation', async () => {
  const f = await fixture();
  let now = START, requests = 0;
  let doc = await f.sign(f.document());
  const lookup = statusVerifier({trust: f.trust, clock: () => now, maxAgeMs: 120_000,
    retrieve: async () => {requests++; return doc;}});
  const first = await Promise.all([lookup(f.entry(7)), lookup(f.entry(8))]);
  assert(first.every(result => !result.revoked));
  assert.equal(requests, 1);
  now += 59_999;
  assert.equal((await lookup(f.entry(7))).source, 'cache');
  now += 1;
  doc = await f.sign(f.document({time: now, revoked: [7]}), now);
  assert.deepEqual(await lookup(f.entry(7)), {revoked: true, source: 'retrieved', published: now});
  assert.equal((await lookup(f.entry(8))).revoked, false);
  assert.equal(requests, 2);
});

test('reject changed payload, different signing key, list URL, purpose, and out-of-range index', async () => {
  const f = await fixture(), other = await fixture();
  const signed = await f.sign(f.document());
  const tampered = structuredClone(signed);
  tampered.credentialSubject.encodedList = encodeList([7]);
  const lookup = doc => statusVerifier({trust: f.trust, clock: () => START, maxAgeMs: 120_000, retrieve: async () => doc});
  await assert.rejects(lookup(tampered)(f.entry(7)), /STATUS_SIGNATURE/);
  await assert.rejects(lookup(await other.sign(other.document()))(f.entry(7)), /STATUS_PROOF/);
  await assert.rejects(lookup(signed)({...f.entry(7), statusPurpose: 'suspension'}), /STATUS_ENTRY/);
  await assert.rejects(lookup(signed)({...f.entry(7), statusListCredential: 'https://other.example/list'}), /STATUS_ENTRY/);
  await assert.rejects(lookup(signed)(f.entry(131072)), /STATUS_INDEX/);
});

test('re-fetching an old signature never extends its age; exact expiry and future publication are rejected', async () => {
  const f = await fixture();
  const doc = await f.sign(f.document({ttl: 1000}));
  let now = START;
  const lookup = statusVerifier({trust: f.trust, clock: () => now, maxAgeMs: 10_000, retrieve: async () => doc});
  await lookup(f.entry(7));
  now += 9000;
  await lookup(f.entry(7));
  now += 1000;
  await assert.rejects(lookup(f.entry(7)), /STATUS_STALE_OR_EXPIRED/);
  const short = await f.sign(f.document({lifetime: 1000}));
  const check = statusVerifier({trust: f.trust, clock: () => now, maxAgeMs: 10_000, retrieve: async () => short});
  now = START + 1000;
  await assert.rejects(check(f.entry(7)), /STATUS_STALE_OR_EXPIRED/);
  now = START - 1;
  await assert.rejects(check(f.entry(7)), /STATUS_STALE_OR_EXPIRED/);
});

test('refuse a signed rollback and an alternative signed list at the same publication time', async () => {
  const f = await fixture();
  const older = await f.sign(f.document());
  let now = START + 1000;
  let doc = await f.sign(f.document({time: now, revoked: [7], ttl: 1}), now);
  const alternative = await f.sign(f.document({time: now, ttl: 1}), now);
  const lookup = statusVerifier({trust: f.trust, clock: () => now, maxAgeMs: 10_000, retrieve: async () => doc});
  assert.equal((await lookup(f.entry(7))).revoked, true);
  now += 1;
  doc = older;
  await assert.rejects(lookup(f.entry(7)), /STATUS_ROLLBACK/);
  doc = alternative;
  await assert.rejects(lookup(f.entry(7)), /STATUS_ROLLBACK/);
});

test('outage reuses only an authenticated list within its age limit', async () => {
  const f = await fixture();
  const doc = await f.sign(f.document({ttl: 1000}));
  let now = START, available = true;
  const lookup = statusVerifier({trust: f.trust, clock: () => now, maxAgeMs: 5000,
    retrieve: async () => { if (!available) throw Error('offline'); return doc; }});
  await lookup(f.entry(7));
  available = false;
  now = START + 4999;
  assert.equal((await lookup(f.entry(7))).source, 'cache_during_outage');
  now += 1;
  await assert.rejects(lookup(f.entry(7)), /STATUS_UNAVAILABLE/);
});
