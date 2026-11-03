import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
process.chdir(root); fs.mkdirSync('build',{recursive:true});
const digest=(p,algorithm='sha256')=>crypto.createHash(algorithm).update(fs.readFileSync(p)).digest('hex');
const run=args=>{
  console.log(`> ${args.slice(0,5).join(' ')}`);
  const p=spawnSync(process.execPath,args,{stdio:'inherit'});
  if(p.status!==0)throw new Error(`Setup command failed (${p.status}): ${args.slice(0,5).join(' ')}`);
};
const cli='node_modules/snarkjs/cli.js';
const circuitHash=digest('circuits/access.circom'), lockHash=digest('package-lock.json');
const artifacts={zkey_sha256:'build/access_final.zkey',wasm_sha256:'build/access_js/access.wasm',
  r1cs_sha256:'build/access.r1cs',verifier_sha256:'build/Verifier.sol',verification_key_sha256:'build/verification_key.json'};
const previous=fs.existsSync('build/setup.json')?JSON.parse(fs.readFileSync('build/setup.json')):null;
if(previous?.circuit_sha256===circuitHash&&previous?.lock_sha256===lockHash&&
   Object.entries(artifacts).every(([key,p])=>fs.existsSync(p)&&previous[key]===digest(p))) {
  console.log('Reusing verified matching demonstration artifacts; phase 2 is NOT production-safe.');process.exit(0);
}
run(['node_modules/circom2/cli.js','circuits/access.circom','--r1cs','--wasm','--sym','--O2','-l','node_modules','-o','build']);
run([cli,'r1cs','info','build/access.r1cs']);
const pot='build/powersOfTau28_hez_final_14.ptau';
const expected='eeefbcf7c3803b523c94112023c7ff89558f9b8e0cf5d6cdcba3ade60f168af4a181c9c21774b94fbae6c90411995f7d854d02ebd93fb66043dbb06f17a831c1';
const sources=['https://circom.info/powersOfTau28_hez_final_14.ptau','https://storage.googleapis.com/zkevm/ptau/powersOfTau28_hez_final_14.ptau'];
let potSource=previous?.phase1_source??'preexisting file validated against published BLAKE2b-512';
if(!fs.existsSync(pot)||digest(pot,'blake2b512')!==expected) {
  let ok=false;
  for(const url of sources) {
    console.log(`Downloading public phase-1 ceremony transcript: ${url}`);
    const p=spawnSync('curl',['--fail','--location','--retry','1','--connect-timeout','15','--max-time','120','--output',pot+'.part',url],{stdio:'inherit'});
    if(p.status===0&&digest(pot+'.part','blake2b512')===expected){fs.renameSync(pot+'.part',pot);potSource=url;ok=true;break;}
    if(fs.existsSync(pot+'.part'))fs.unlinkSync(pot+'.part');
  }
  if(!ok)throw new Error('Cannot obtain hash-verified public powers of tau; no insecure silent fallback.');
}
run([cli,'groth16','setup','build/access.r1cs',pot,'build/access_0.zkey']);
run([cli,'zkey','contribute','build/access_0.zkey','build/access_1.zkey','--name=local-demo-contribution-1',`-e=${crypto.randomBytes(64).toString('hex')}`]);
run([cli,'zkey','contribute','build/access_1.zkey','build/access_final.zkey','--name=local-demo-contribution-2',`-e=${crypto.randomBytes(64).toString('hex')}`]);
run([cli,'zkey','verify','build/access.r1cs',pot,'build/access_final.zkey']);
run([cli,'zkey','export','verificationkey','build/access_final.zkey','build/verification_key.json']);
run([cli,'zkey','export','solidityverifier','build/access_final.zkey','build/Verifier.sol']);
fs.writeFileSync('build/setup.json',JSON.stringify({circuit_sha256:circuitHash,lock_sha256:lockHash,
  ...Object.fromEntries(Object.entries(artifacts).map(([key,p])=>[key,digest(p)])),
  phase1_source:potSource,phase1_blake2b512:expected,
  phase1_provenance:'Public Perpetual Powers of Tau transcript, hash pinned to iden3/snarkjs table',
  phase2_status:'Two contributions from this one local process; NOT independent participants and NOT production-safe',
  created_utc:new Date().toISOString()},null,2)+'\n');
