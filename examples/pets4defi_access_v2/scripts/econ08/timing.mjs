// Run this entry point in THREE separate processes, ten measured repetitions
// each. Nothing from replay or Solidity compilation is included in these clocks.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
import * as snarkjs from 'snarkjs';

process.chdir(path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'));
const [evidence,sessionText]=process.argv.slice(2),session=Number(sessionText);
assert(evidence&&Number.isInteger(session)&&session>=1&&session<=3,
  'Usage: node scripts/econ08/timing.mjs RESULTS_DIR SESSION_ID(1..3)');
const dir=path.resolve(evidence),out=path.join(dir,'timing');fs.mkdirSync(out,{recursive:true});
const target=path.join(out,`session_${session}.json`);assert(!fs.existsSync(target),'Refusing to replace a timing session');
const raw=JSON.parse(gunzipSync(fs.readFileSync(path.join(dir,'receipts_and_proofs.json.gz'))));
const sample=raw.proofs.find(p=>p.scenario==='zk_B1_d0_LOW'&&p.purpose==='workload');assert(sample);
const vk=JSON.parse(fs.readFileSync(path.join(dir,'verification_key.json')));
const sha=x=>createHash('sha256').update(x).digest('hex');
const report=JSON.parse(fs.readFileSync(path.join(dir,'report.json')));
assert.equal(sha(fs.readFileSync('build/access_final.zkey')),report.setup.zkey_sha256);
assert.equal(sha(fs.readFileSync('build/access_js/access.wasm')),report.setup.wasm_sha256);
const observations=[];
for(let i=-1;i<10;i++) {
  const start=performance.now();
  const {proof,publicSignals}=await snarkjs.groth16.fullProve(sample.input,'build/access_js/access.wasm','build/access_final.zkey',undefined,undefined,{singleThread:true});
  const proofMs=performance.now()-start,verifyStart=performance.now();
  assert.equal(await snarkjs.groth16.verify(vk,publicSignals,proof),true);
  const verifyMs=performance.now()-verifyStart;
  observations.push({iteration:i,warmup:i===-1,proof_ms:proofMs,verify_ms:verifyMs,proof,publicSignals});
}
const result={schema_version:1,session,created_utc:new Date().toISOString(),pid:process.pid,node:process.version,
  cpu:os.cpus()[0]?.model,logical_cpus:os.cpus().length,input:sample.input,
  zkey_sha256:report.setup.zkey_sha256,wasm_sha256:report.setup.wasm_sha256,
  operation:'singleThread fullProve including witness construction; verification measured separately',
  observations,limits:'One fixed synthetic input and one device. Three fresh processes are not three machines or populations. One unmeasured warm-up per process. No concurrent experiment process.'};
fs.writeFileSync(target,JSON.stringify(result,null,2)+'\n');
console.log(`PASS timing session ${session}: 10 observations + 1 excluded warm-up`);
process.exit(0);
