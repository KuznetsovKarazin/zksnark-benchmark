// Verify retained v0.5 calibration signed transactions and source bindings.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {ethers} from 'ethers';
process.chdir(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..'));
const root='../../projects/pets4defi/econ08/technical_followup_v05';
const hash=x=>createHash('sha256').update(x).digest('hex');
const report=JSON.parse(gunzipSync(fs.readFileSync(`${root}/unchecked_calibration/receipts.json.gz`)));
assert.equal(report.status,'PASS');
for(const [file,digest] of Object.entries(report.source_hashes))assert.equal(hash(fs.readFileSync(file)),digest,file);
let transactions=0;
for(const run of report.runs){
  const seen=new Set();
  for(const row of run.transactions){
    const tx=ethers.Transaction.from(row.signed_serialized);
    assert.equal(tx.hash,row.receipt.hash);assert.equal(tx.from,row.receipt.from);
    assert.equal(tx.data,row.transaction.data);assert.equal(tx.to,row.receipt.to);
    assert.equal(row.gas,Number(row.receipt.gasUsed));assert.equal(row.receipt.status,1);
    assert(!seen.has(tx.hash));seen.add(tx.hash);transactions++;
  }
  const included=run.transactions.filter(t=>['approval','access'].includes(t.category));
  assert.equal(included.length,404);
  assert.equal(included.reduce((s,t)=>s+t.gas,0),run.summary.common_K05_gas);
  for(const a of run.accesses)assert(seen.has(a.tx_hash));
}
console.log(JSON.stringify({status:'PASS',calibration_runs:3,accesses:1200,signed_transactions:transactions}));
