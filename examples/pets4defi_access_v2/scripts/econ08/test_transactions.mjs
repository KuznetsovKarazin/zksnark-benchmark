import fs from 'node:fs';
import assert from 'node:assert/strict';
import test from 'node:test';
import {gunzipSync} from 'node:zlib';
import {verifyTransactions} from './verify_transactions.mjs';

const raw=JSON.parse(gunzipSync(fs.readFileSync(new URL('../../results/econ08_native_pilot/receipts_and_proofs.json.gz',import.meta.url))));
const sample=raw.transactions.find(t=>t.proof_index===0);
test('original archived transaction signature and hash match',()=>{
  assert.equal(verifyTransactions([sample]),1);
});
test('changed calldata cannot retain the archived signed transaction hash',()=>{
  const changed=structuredClone(sample);
  const data=changed.transaction.data;
  changed.transaction.data=data.slice(0,-1)+(data.endsWith('0')?'1':'0');
  assert.throws(()=>verifyTransactions([changed]));
});
