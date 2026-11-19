import {gzipSync, gunzipSync} from 'node:zlib';
import {DataIntegrityProof} from '@digitalbazaar/data-integrity';
import {createSignCryptosuite, createVerifyCryptosuite} from '@digitalbazaar/eddsa-jcs-2022-cryptosuite';
import jsigs from 'jsonld-signatures';

export const LIST_BYTES = 16_384;
export const VC_CONTEXT = 'https://www.w3.org/ns/credentials/v2';
const {AssertionProofPurpose} = jsigs.purposes;

function requireStatus(condition, code) {
  if (!condition) throw new Error(code);
}

function bitLocation(index) {
  requireStatus(Number.isSafeInteger(index) && index >= 0 && index < LIST_BYTES * 8, 'STATUS_INDEX');
  return [Math.floor(index / 8), 0x80 >> (index % 8)];
}

export function encodeList(revoked) {
  const bytes = Buffer.alloc(LIST_BYTES);
  for (const index of revoked) {
    const [offset, mask] = bitLocation(index);
    bytes[offset] |= mask;
  }
  return `u${gzipSync(bytes).toString('base64url')}`;
}

export function expandList(encoded) {
  requireStatus(typeof encoded === 'string' && encoded.length <= 32_768 && /^u[A-Za-z0-9_-]+$/.test(encoded), 'STATUS_ENCODING');
  const compressed = Buffer.from(encoded.slice(1), 'base64url');
  requireStatus(`u${compressed.toString('base64url')}` === encoded, 'STATUS_ENCODING');
  let bytes;
  try { bytes = gunzipSync(compressed, {maxOutputLength: LIST_BYTES}); }
  catch { throw new Error('STATUS_ENCODING'); }
  requireStatus(bytes.length === LIST_BYTES, 'STATUS_LENGTH');
  return bytes;
}

export function isRevoked(bytes, index) {
  const [offset, mask] = bitLocation(index);
  return Boolean(bytes[offset] & mask);
}

export async function signList(document, signer, documentLoader, time) {
  return jsigs.sign(structuredClone(document), {documentLoader, purpose: new AssertionProofPurpose(),
    suite: new DataIntegrityProof({signer, date: new Date(time), cryptosuite: createSignCryptosuite()})});
}

function timestamp(value) {
  requireStatus(typeof value === 'string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?Z$/.test(value), 'STATUS_TIMESTAMP');
  const time = Date.parse(value);
  const canonical = value.includes('.') ? value : `${value.slice(0, -1)}.000Z`;
  requireStatus(Number.isSafeInteger(time) && new Date(time).toISOString() === canonical, 'STATUS_TIMESTAMP');
  return time;
}

export async function verifyList(document, trust) {
  requireStatus(document?.id === trust.url && document.issuer === trust.issuer, 'STATUS_ISSUER_OR_URL');
  requireStatus(Array.isArray(document['@context']) && document['@context'][0] === VC_CONTEXT &&
    Array.isArray(document.type) && document.type.includes('VerifiableCredential') &&
    document.type.includes('BitstringStatusListCredential'), 'STATUS_TYPE');
  const subject = document.credentialSubject;
  requireStatus(subject?.type === 'BitstringStatusList' && subject.statusPurpose === 'revocation' &&
    (subject.statusSize === undefined || subject.statusSize === 1), 'STATUS_PURPOSE');
  const proof = document.proof;
  requireStatus(proof?.type === 'DataIntegrityProof' && proof.cryptosuite === 'eddsa-jcs-2022' &&
    proof.proofPurpose === 'assertionMethod' && proof.verificationMethod === trust.keyId, 'STATUS_PROOF');
  const verified = await jsigs.verify(document, {documentLoader: trust.documentLoader,
    purpose: new AssertionProofPurpose(), suite: new DataIntegrityProof({cryptosuite: createVerifyCryptosuite()})});
  requireStatus(verified.verified, 'STATUS_SIGNATURE');
  const published = timestamp(document.validFrom), expires = timestamp(document.validUntil);
  requireStatus(expires > published && timestamp(proof.created) === published, 'STATUS_VALIDITY');
  const ttl = subject.ttl;
  requireStatus(ttl === undefined || Number.isSafeInteger(ttl) && ttl >= 0, 'STATUS_TTL');
  return {published, expires, ttl, version: proof.proofValue, encoded: subject.encodedList};
}

// One verifier and one allowlisted issuer/list. The caller supplies a bounded
// retrieval function and an already authenticated credential status entry.
export function statusVerifier({trust, retrieve, maxAgeMs, clock = Date.now}) {
  requireStatus(Number.isSafeInteger(maxAgeMs) && maxAgeMs > 0, 'STATUS_MAX_AGE');
  let current;
  let refresh;
  const usable = (item, now) => item && now >= item.published &&
    now < item.expires && now - item.published < maxAgeMs;
  return async entry => {
    requireStatus(entry?.type === 'BitstringStatusListEntry' && entry.statusListCredential === trust.url &&
      entry.statusPurpose === 'revocation', 'STATUS_ENTRY');
    requireStatus(typeof entry.statusListIndex === 'string' && /^\d+$/.test(entry.statusListIndex), 'STATUS_INDEX');
    const index = Number(entry.statusListIndex);
    bitLocation(index);
    let source = 'cache';
    if (!usable(current, clock()) || clock() - current.retrieved >= (current.ttl ?? Infinity)) {
      refresh ??= (async () => {
        let document;
        try { document = await retrieve(trust.url); }
        catch {
          requireStatus(usable(current, clock()), 'STATUS_UNAVAILABLE');
          return 'cache_during_outage';
        }
        const item = await verifyList(document, trust);
        requireStatus(usable(item, clock()), 'STATUS_STALE_OR_EXPIRED');
        requireStatus(!current || item.published > current.published ||
          item.published === current.published && item.version === current.version, 'STATUS_ROLLBACK');
        current = {...item, bytes: expandList(item.encoded), retrieved: clock()};
        return 'retrieved';
      })().finally(() => { refresh = undefined; });
      source = await refresh;
    }
    requireStatus(usable(current, clock()), 'STATUS_STALE_OR_EXPIRED');
    return {revoked: isRevoked(current.bytes, index), source, published: current.published};
  };
}
