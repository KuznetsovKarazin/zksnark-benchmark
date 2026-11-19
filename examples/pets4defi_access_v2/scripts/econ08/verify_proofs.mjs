// Verify archived cryptography and signed transaction hashes without obtaining
// or regenerating a proving key. Accept multiple independent evidence folders.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {gunzipSync} from 'node:zlib';
import * as snarkjs from 'snarkjs';
import {verifyTransactions} from './verify_transactions.mjs';

const args=process.argv.slice(2);
let expected=null;
if(args[0]==='--expected-proofs') {
  expected=Number(args[1]);
  assert(Number.isInteger(expected)&&expected>=0);
  args.splice(0,2);
}
assert(args.length,'Usage: node scripts/econ08/verify_proofs.mjs [--expected-proofs N] RESULTS_DIR...');
let verified=0,transactions=0,tamperChecks=0;
for(const dir of args) {
  const vk=JSON.parse(fs.readFileSync(path.join(dir,'verification_key.json')));
  const raw=JSON.parse(gunzipSync(fs.readFileSync(path.join(dir,'receipts_and_proofs.json.gz'))));
  transactions+=verifyTransactions(raw.transactions);
  for(const p of raw.proofs) {
    assert.equal(await snarkjs.groth16.verify(vk,p.publicSignals,p.proof),true,`${dir}/proof ${p.index}`);
    verified++;
  }
  const timing=path.join(dir,'timing');
  if(fs.existsSync(timing))for(const name of fs.readdirSync(timing).filter(n=>/^session_[123]\.json$/.test(n))) {
    const session=JSON.parse(fs.readFileSync(path.join(timing,name)));
    for(const p of session.observations) {
      assert.equal(await snarkjs.groth16.verify(vk,p.publicSignals,p.proof),true,`${dir}/${name}/${p.iteration}`);
      verified++;
    }
  }
  // Signed controls legitimately have no proofs. Each ZK archive gets its own
  // negative check against that archive's independently stored verification key.
  if(raw.proofs.length) {
    const p=raw.proofs[0],mutated=[...p.publicSignals];
    mutated[7]=(BigInt(mutated[7])+1n).toString();
    assert.equal(await snarkjs.groth16.verify(vk,mutated,p.proof),false);
    tamperChecks++;
  }
}
if(expected!==null)assert.equal(verified,expected,'unexpected archived proof count');
console.log(JSON.stringify({status:'PASS',folders:args.length,verified_proofs:verified,
  signed_transactions:transactions,public_input_tamper_checks:tamperChecks}));
process.exit(0);
