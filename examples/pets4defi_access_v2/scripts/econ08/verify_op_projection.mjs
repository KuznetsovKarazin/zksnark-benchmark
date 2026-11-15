// Offline reconstruction of every historical OP quote; makes no network calls.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {ethers} from 'ethers';
process.chdir(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..'));
const root='../../projects/pets4defi/econ08/technical_followup_v05/op_projection';
const p=JSON.parse(fs.readFileSync(`${root}/projection.json`));
const raw=JSON.parse(fs.readFileSync(`${root}/rpc_evidence.json`));
const sha=x=>createHash('sha256').update(x).digest('hex');
const abi=new ethers.Interface(['function getL1Fee(bytes) view returns(uint256)','function getOperatorFee(uint256) view returns(uint256)']);
const tag=ethers.toQuantity(p.block),price=BigInt(p.effective_execution_price_wei);
const snapshot=JSON.parse(fs.readFileSync('results/fee_snapshot.json'));
const op=Object.values(snapshot).filter(Array.isArray).flat().find(x=>x.observed_chain_id===10);
assert(op);assert.equal(BigInt(op.summary.within_block_effective_p50_block_weighted.p50_wei),price);
assert.equal(op.observed_head.hash,p.block_hash);
const responses=new Map();
for(const r of raw){
  assert.equal(r.request.id,r.response.id);assert(!r.response.error);
  responses.set(JSON.stringify([r.request.method,r.request.params]),r.response.result);
}
function response(method,params){const result=responses.get(JSON.stringify([method,params]));assert.notEqual(result,undefined);return result;}
const block=response('eth_getBlockByNumber',[tag,false]);
assert.equal(block.hash,p.block_hash);assert.equal(parseInt(block.timestamp,16),p.block_timestamp);
assert.equal(BigInt(response('eth_chainId',[])),10n);
const base=BigInt(block.baseFeePerGas);
const quote=(method,arg)=>abi.decodeFunctionResult(method,response('eth_call',[{to:p.oracle,data:abi.encodeFunctionData(method,[arg])},tag]))[0];
let count=0;
for(const schedule of ['weekly','control']){
  const dir=`results/econ08_cohort/runs/N16_zk_B2_d0_HIGH_${schedule}`;
  const file=`${dir}/receipts_and_proofs.json.gz`;
  assert.equal(sha(fs.readFileSync(file)),p.input_hashes[file]);
  const context=JSON.parse(fs.readFileSync(`${dir}/report.json`)).context;
  const source=JSON.parse(gunzipSync(fs.readFileSync(file))).transactions.filter(t=>!t.excluded_from_system_cost&&['approval','access','deployment','partition_setup','initial_publication','status_publication'].includes(t.category));
  const rows=p.rows.filter(r=>r.schedule===schedule);assert.equal(rows.length,source.length);
  for(let i=0;i<source.length;i++){
    const t=source[i],tx=t.transaction,g=BigInt(t.receipt.gasUsed),r=rows[i];
    const unsigned=ethers.Transaction.from({type:2,chainId:10,nonce:tx.nonce,gasLimit:tx.gasLimit,
      maxFeePerGas:price,maxPriorityFeePerGas:price-base,to:tx.to,value:tx.value,data:tx.data,accessList:tx.accessList??[]}).unsignedSerialized;
    assert.equal(sha(unsigned),r.unsigned_sha256);assert.equal(r.source_tx_hash,t.receipt.hash);
    assert.equal(r.actor,t.actor);assert.equal(r.category,t.category);assert.equal(r.t,t.timestamp-(context.base-3600));
    assert.equal(r.gas,Number(g));assert.equal(BigInt(r.execution_wei),g*price);
    assert.equal(BigInt(r.l1_data_wei),quote('getL1Fee',unsigned));
    assert.equal(BigInt(r.operator_wei),quote('getOperatorFee',g));
    assert.equal(BigInt(r.total_wei),BigInt(r.execution_wei)+BigInt(r.l1_data_wei)+BigInt(r.operator_wei));
    count++;
  }
}
assert.equal(count,848);
console.log(JSON.stringify({status:'PASS',offline_OP_quotes:count,rpc_evidence_records:raw.length,block:p.block}));
