import * as Ed25519 from '@digitalbazaar/ed25519-multikey';
import {contexts} from '@digitalbazaar/credentials-context';
import multikeyContext from '@digitalbazaar/multikey-context';
import {VC_CONTEXT, encodeList, signList} from './status.mjs';

export const START = Date.parse('2026-10-20T12:00:00.000Z');

export async function fixture() {
  const issuer = 'https://issuer.example/econ08', url = `${issuer}/status/revocation`;
  const pair = await Ed25519.generate({controller: issuer});
  const key = await pair.export({publicKey: true, includeContext: true});
  const documents = new Map(contexts);
  for (const [url, context] of multikeyContext.contexts) documents.set(url, context);
  documents.set(key.id, key);
  documents.set(issuer, {'@context': 'https://w3id.org/security/v2', id: issuer, assertionMethod: [key.id]});
  const trust = {issuer, url, keyId: key.id, documentLoader: async url => {
    if (!documents.has(url)) throw new Error(`Unconfigured document: ${url}`);
    return {contextUrl: null, documentUrl: url, document: structuredClone(documents.get(url))};
  }};
  const entry = index => ({id: `${url}#${index}`, type: 'BitstringStatusListEntry',
    statusPurpose: 'revocation', statusListCredential: url, statusListIndex: String(index)});
  const document = ({time = START, lifetime = 86_400_000, ttl = 60_000, revoked = [], encoded = encodeList(revoked)} = {}) => ({
    '@context': [VC_CONTEXT], id: url, type: ['VerifiableCredential', 'BitstringStatusListCredential'], issuer,
    validFrom: new Date(time).toISOString(), validUntil: new Date(time + lifetime).toISOString(),
    credentialSubject: {id: `${url}#list`, type: 'BitstringStatusList', statusPurpose: 'revocation', encodedList: encoded, ttl},
  });
  const sign = (doc, time = START) => signList(doc, pair.signer(), trust.documentLoader, time);
  return {trust, entry, document, sign, key};
}
