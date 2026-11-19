// Independently verify released public calldata and archived Groth16 proofs.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import * as snarkjs from 'snarkjs';
import {extract,gateABI} from './extractor.mjs';
const root=path.resolve('../../projects/pets4defi/econ08/empirical_v03/results');
const vkFile=path.join(root,'evm_setup/verification_key.json');
const vk=JSON.parse(fs.readFileSync(vkFile));
const digest=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const summaries=[];
for(const n of [32,128]) {
  const folder=path.join(root,`evm_N${n}`),reportFile=path.join(folder,'report.json');
  assert(fs.existsSync(reportFile),`Missing completed ${n}-holder report`);
  const report=JSON.parse(fs.readFileSync(reportFile));assert.equal(report.status,'PASS');
  assert.equal(digest(vkFile),report.setup.verification_key_sha256);
  const records=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(folder,'public_records.json.gz'))));
  assert.equal(records.length,report.transactions);
  assert.equal(new Set(records.map(r=>r.transaction.hash)).size,records.length);
  const extracted=records.map(r=>extract(r,report.extractor_config));
  let verified=0;
  for(let i=0;i<records.length;i++) {
    if(extracted[i].kind!=='full_zk')continue;
    const call=gateABI.parseTransaction({data:records[i].transaction.input??records[i].transaction.data});
    const p=call.args.proof;
    const proof={pi_a:[String(p.a[0]),String(p.a[1]),'1'],
      pi_b:[[String(p.b[0][1]),String(p.b[0][0])],[String(p.b[1][1]),String(p.b[1][0])],['1','0']],
      pi_c:[String(p.c[0]),String(p.c[1]),'1'],protocol:'groth16',curve:'bn128'};
    assert(await snarkjs.groth16.verify(vk,Array.from(p.publicSignals,String),proof),`Invalid proof ${extracted[i].tx_hash}`);
    verified++;
  }
  for(const kind of ['full_zk','hit','publication']) assert.deepEqual(extracted.filter(r=>r.kind===kind).map(r=>Number(r.fees.gas_used)),report.gas_by_kind[kind]);
  assert.equal(extracted.filter(r=>['full_zk','hit'].includes(r.kind)).length,report.accesses);
  summaries.push({holders:n,transactions:records.length,accesses:report.accesses,groth16_proofs_verified:verified,classification_mismatches:0});
}
const result={status:'PASS',input:'Public transaction calldata, receipts, block headers and verification key only',runs:summaries};
const out=process.argv[2]??path.join(root,'public_proof_audit.json');fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));process.exit(0);
