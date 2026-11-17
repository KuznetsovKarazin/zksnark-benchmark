// The evaluator may see the old truth labels; extractor.mjs may not.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {extract,gateABI,fees} from './extractor.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const dest=process.argv[2]??path.join(root,'../../projects/pets4defi/econ08/empirical_v03/results/extractor_validation.json');
const walk=d=>fs.readdirSync(d,{withFileTypes:true}).flatMap(x=>x.isDirectory()?walk(path.join(d,x.name)):[path.join(d,x.name)]);
const files=walk(path.join(root,'results')).filter(x=>x.endsWith('receipts_and_proofs.json.gz'));
const rows=[];let exemplar;
for(const file of files) {
  const raw=fs.readFileSync(file),archive=JSON.parse(zlib.gunzipSync(raw));
  // These address lists describe deployed contracts, not holder/issuer labels.
  // Live runs obtain the same allowlists from a deployment manifest and code hash.
  const gates=archive.transactions.filter(x=>x.category==='deployment'&&x.component==='PolicyGate').map(x=>x.receipt.contractAddress);
  const registries=archive.transactions.filter(x=>x.category==='deployment'&&x.component==='PolicyRegistry').map(x=>x.receipt.contractAddress);
  const config={gates,registries,chainId:archive.transactions[0].transaction.chainId,chainType:'l1'};
  let accesses=0,mismatches=0,reverted=0,publications=0;
  for(const item of archive.transactions) {
    const sanitized={transaction:item.transaction,receipt:item.receipt,
      block:{number:item.receipt.blockNumber,hash:item.receipt.blockHash,timestamp:item.timestamp}};
    const extracted=extract(sanitized,config);
    if(extracted.kind==='reverted') reverted++;
    if(extracted.kind==='publication') publications++;
    if(item.category==='access'&&BigInt(item.receipt.status)===1n) {
      accesses++;
      const truth=item.event==='hit'?'hit':item.proof_index==null?'full_signed':'full_zk';
      if(truth!==extracted.kind) mismatches++;
      exemplar??={sanitized,config};
      // Poison every private field; public-only reconstruction must be invariant.
      assert.deepEqual(extract({...sanitized,holder_issuer:999,event:'fabricated',proofs:[{secret:'POISON'}]},config),extracted);
    }
  }
  rows.push({archive:path.relative(root,file),sha256:crypto.createHash('sha256').update(raw).digest('hex'),transactions:archive.transactions.length,accesses,mismatches,reverted,publications});
}
assert(exemplar,'No access fixtures');
assert.equal(rows.reduce((s,x)=>s+x.mismatches,0),0,'Archived truth mismatch');
const clone=()=>structuredClone(exemplar.sanitized);
let bad=clone();bad.block.hash='0x'+'00'.repeat(32);assert.throws(()=>extract(bad,exemplar.config));
bad=clone();bad.receipt.status=0;bad.receipt.logs=[];assert.equal(extract(bad,exemplar.config).kind,'reverted');
bad=clone();bad.receipt.logs=[];assert.throws(()=>extract(bad,exemplar.config));
bad=clone();bad.transaction.data='0xdeadbeef';assert.equal(extract(bad,exemplar.config).kind,'unsupported_gate_call');
assert.equal(fees({gasUsed:100,effectiveGasPrice:2},{chainType:'op'}).total_wei,null);
assert.equal(fees({gasUsed:100,effectiveGasPrice:2,l1Fee:7,operatorFeeScalar:10,operatorFeeConstant:3},{chainType:'op',operatorFeeModel:'jovian'}).total_wei,'100210');
const report={status:'PASS',scope:'Offline archived local-EVM transactions; not a public-testnet result. Block timestamps were archived by the harness, not re-fetched from a public chain.',
  files:rows.length,transactions:rows.reduce((s,x)=>s+x.transactions,0),accesses:rows.reduce((s,x)=>s+x.accesses,0),mismatches:0,
  negative_tests:['private-metadata-poisoning','block-hash-mismatch','reverted-call','missing-event','unsupported-selector','unknown-fee-components','jovian-fee-formula'],rows};
fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({...report,rows:undefined}));
