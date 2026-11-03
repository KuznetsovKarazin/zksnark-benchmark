import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {performance} from 'node:perf_hooks';
import {spawnSync} from 'node:child_process';
import {groth16} from 'snarkjs';

const file=fileURLToPath(import.meta.url),root=path.resolve(path.dirname(file),'..');
process.chdir(root);
const child=process.argv.includes('--child');
const inputFile=child?process.argv[process.argv.indexOf('--input')+1]:'build/prover_input_snapshot.json';
if(!child)fs.copyFileSync('build/browser_input.json',inputFile);
const input=JSON.parse(fs.readFileSync(inputFile));
const vk=JSON.parse(fs.readFileSync('build/verification_key.json'));
const wasm='build/access_js/access.wasm',zkey='build/access_final.zkey';
async function sample(){
  const t=performance.now();
  const {proof,publicSignals}=await groth16.fullProve(input,wasm,zkey,undefined,undefined,{singleThread:true});
  const proof_time_ms=performance.now()-t;
  const v=performance.now();
  const valid=await groth16.verify(vk,publicSignals,proof);
  if(valid!==true)throw new Error('Strict verification failed');
  return {proof_time_ms,verification_time_ms:performance.now()-v,verified:true};
}
if(child){
  process.stdout.write(JSON.stringify(await sample())+'\n');process.exit(0);
}
const n=Number(process.env.PROVER_RUNS??30);
if(!Number.isInteger(n)||n<1)throw new Error('Invalid PROVER_RUNS');
const quantile=(xs,p)=>{const a=[...xs].sort((a,b)=>a-b),j=(a.length-1)*p,l=Math.floor(j);return a[l]+(a[Math.ceil(j)]-a[l])*(j-l);};
const stats=xs=>({n:xs.length,median:quantile(xs,.5),q1:quantile(xs,.25),q3:quantile(xs,.75),iqr:quantile(xs,.75)-quantile(xs,.25),min:Math.min(...xs),max:Math.max(...xs)});
const cold=[],warm=[];
for(let i=0;i<n;i++){
  const t=performance.now(),r=spawnSync(process.execPath,[file,'--child','--input',inputFile],{encoding:'utf8',timeout:120000,maxBuffer:1024*1024});
  if(r.status!==0)throw new Error(`Cold proof ${i} failed: ${r.stderr}`);
  cold.push({run:i+1,...JSON.parse(r.stdout.trim()),process_wall_ms:performance.now()-t});
  console.log(`Cold process ${i+1}/${n}`);
}
const excludedWarmup=await sample();
for(let i=0;i<n;i++)warm.push({run:i+1,...await sample()});
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
fs.mkdirSync('results',{recursive:true});
fs.writeFileSync('results/server_prover.json',JSON.stringify({schema_version:1,
  evidence_status:'measured_local_server',created_utc:new Date().toISOString(),node:process.version,
  cpu:os.cpus()[0]?.model,logical_cpus:os.cpus().length,total_memory_bytes:os.totalmem(),platform:process.platform,arch:process.arch,
  mode:'single-thread fullProve; default snarkjs verification; sequential samples',
  cold_definition:'Fresh Node process for each proof. OS filesystem cache is not flushed; this is not cold hardware or browser startup.',
  proof_timer:'fullProve includes witness generation and artifact reads; excludes separate verification and process startup',
  circuit_sha256:hash('circuits/access.circom'),wasm_sha256:hash(wasm),zkey_sha256:hash(zkey),input_sha256:hash(inputFile),
  publishable_sample_count:n>=30,excluded_warmup:excludedWarmup,cold,warm,
  summary:{cold_proof_ms:stats(cold.map(x=>x.proof_time_ms)),cold_process_wall_ms:stats(cold.map(x=>x.process_wall_ms)),warm_proof_ms:stats(warm.map(x=>x.proof_time_ms))},
  browser_status:'Unmeasured in this file; use browser harness on an actual device',phone_status:'Unmeasured',
},null,2)+'\n');
console.log('Saved verified raw server measurements to results/server_prover.json');
process.exit(0);
