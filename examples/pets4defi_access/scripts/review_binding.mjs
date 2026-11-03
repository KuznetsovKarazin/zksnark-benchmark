// Focused regression experiment; writes only to a new temporary directory.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';

const project=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require=createRequire(project+'/package.json');
const snarkjs=require('snarkjs');
const {buildPoseidon}=require('circomlibjs');
const ptau=path.join(project,'build/pot_final.ptau');
assert.ok(fs.existsSync(ptau),'Run npm run setup before this local review.');
const scratch=fs.mkdtempSync(path.join(os.tmpdir(),'pets4defi-binding-'));
const original=fs.readFileSync(project+'/circuits/eligible.circom','utf8');
const noBind=original.replace('    signal output actionBinding;\n','')
  .replace(/    \/\/ Use the request context[\s\S]*?    actionBinding <== bind.out;\n/,'');
assert.notEqual(noBind,original,'The v1 circuit layout changed; review this extraction.');
assert.ok(!noBind.includes('component bind ='),'The binding component was not removed.');
const toy=alias=>`pragma circom 2.1.9;
template Square() {
 signal input secret; signal input requestHash; signal output square;
 square <== secret * secret;
 ${alias?'signal unusedAlias; unusedAlias <== requestHash + 1;':''}
}
component main {public [requestHash]} = Square();`;
const circuits={unused:toy(false),linear_private:toy(true),eligible_no_bind:noBind,eligible_original:original};
const poseidon=await buildPoseidon();
const results=[];
const run=(script,args)=>execFileSync(process.execPath,[project+'/node_modules/'+script,...args],
  {cwd:project,encoding:'utf8',maxBuffer:5e6});

for(const [name,source] of Object.entries(circuits)) {
  const out=path.join(scratch,name);fs.mkdirSync(out);
  const circuit=path.join(scratch,name+'.circom');fs.writeFileSync(circuit,source);
  run('circom2/cli.js',[circuit,'--r1cs','--wasm','--sym','--O2','--inspect','-l','node_modules','-o',out]);
  run('snarkjs/cli.js',['r1cs','export','json',out+'/'+name+'.r1cs',out+'/r1cs.json']);
  run('snarkjs/cli.js',['groth16','setup',out+'/'+name+'.r1cs',ptau,out+'/initial.zkey']);
  run('snarkjs/cli.js',['zkey','contribute',out+'/initial.zkey',out+'/final.zkey',
    '--name=isolated-binding-review','-e=isolated-test-only-do-not-use-in-production']);
  run('snarkjs/cli.js',['zkey','export','verificationkey',out+'/final.zkey',out+'/vk.json']);
  const vkey=JSON.parse(fs.readFileSync(out+'/vk.json','utf8'));
  const simple=name==='unused'||name==='linear_private';
  const input=simple?{secret:'3',requestHash:'123'}:
    {age:'23',salt:'123456789',commitment:poseidon.F.toString(poseidon([23n,123456789n])),requestHash:'123'};
  const {proof,publicSignals}=await snarkjs.groth16.fullProve(input,out+'/'+name+'_js/'+name+'.wasm',
    out+'/final.zkey',undefined,undefined,{singleThread:true});
  const changed=publicSignals.slice();changed[changed.length-1]='124';
  const verified=await snarkjs.groth16.verify(vkey,publicSignals,proof);
  const changedRequestVerified=await snarkjs.groth16.verify(vkey,changed,proof);
  const r1cs=JSON.parse(fs.readFileSync(out+'/r1cs.json','utf8'));
  const sym=fs.readFileSync(out+'/'+name+'.sym','utf8').split('\n').find(x=>x.endsWith('main.requestHash'));
  assert.ok(sym,'Expected requestHash public signal is missing.');
  const requestWire=Number(sym.split(',')[1]);
  const result={name,nConstraints:r1cs.constraints.length,
    constraintsReferencingRequest:r1cs.constraints.filter(c=>c.some(lc=>Object.hasOwn(lc,String(requestWire)))).length,
    requestICIsZero:vkey.IC.at(-1)[2]==='0',verified,changedRequestVerified,publicSignals,changed};
  results.push(result);console.log(result);
  fs.writeFileSync(scratch+'/results.json',JSON.stringify(results,null,2));
  assert.equal(verified,true);assert.equal(changedRequestVerified,false);assert.equal(result.requestICIsZero,false);
}
console.log('Experimental artifacts:',scratch);
// snarkjs and circomlibjs retain worker pools after all awaited work finishes.
process.exit(0);
