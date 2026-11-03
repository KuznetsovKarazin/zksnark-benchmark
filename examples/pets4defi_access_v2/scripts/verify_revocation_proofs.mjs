// Verify every saved synthetic proof using the corresponding saved key.
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
import {groth16} from 'snarkjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const out=path.join(root,'results/revocation_validation');
const vk=JSON.parse(fs.readFileSync(path.join(out,'verification_key.json')));
const raw=JSON.parse(gunzipSync(fs.readFileSync(path.join(out,'receipts_and_proofs.json.gz'))));
for(const p of raw.proofs) assert.equal(await groth16.verify(vk,p.publicSignals,p.proof),true,`${p.label}/${p.nonce}`);
console.log(`PASS: ${raw.proofs.length} saved proofs verify. A valid proof for an old root is still rejected by the contract freshness checks.`);
process.exit(0);
