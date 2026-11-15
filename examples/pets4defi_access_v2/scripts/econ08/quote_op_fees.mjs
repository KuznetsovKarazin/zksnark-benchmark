// Read-only historical OP fee projection. Never signs or sends transactions.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {ethers} from 'ethers';
process.chdir(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..'));
const out=process.argv[2];assert(out);fs.mkdirSync(out,{recursive:false});
const endpoint='https://mainnet.optimism.io',block=158458797,tag=ethers.toQuantity(block);
const expectedHash='0x4751aa2942644e95811e66e09100ca1cc5218b563aa11ae6620dba1bf4bd0764';
const oracle='0x420000000000000000000000000000000000000F';
const abi=new ethers.Interface(['function getL1Fee(bytes) view returns(uint256)','function getOperatorFee(uint256) view returns(uint256)']);
const price=6661n,raw=[],cache=new Map();let requestId=0;
async function call(method,params){const body={jsonrpc:'2.0',id:++requestId,method,params};
  const res=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(20000)});
  if(!res.ok)throw Error(`RPC HTTP ${res.status}`);const result=await res.json();if(result.error)throw Error(JSON.stringify(result.error));raw.push({request:body,response:result});return result.result;}
const head=await call('eth_getBlockByNumber',[tag,false]);assert.equal(head.hash,expectedHash);
assert.equal(BigInt(await call('eth_chainId',[])),10n);
const base=BigInt(head.baseFeePerGas);assert(price>=base);
async function quote(method,arg){const data=abi.encodeFunctionData(method,[arg]);
  if(!cache.has(data))cache.set(data,call('eth_call',[{to:oracle,data},tag]).then(result=>abi.decodeFunctionResult(method,result)[0]));
  return await cache.get(data);}
const rows=[];
for(const schedule of ['weekly','control']){
  const dir=`results/econ08_cohort/runs/N16_zk_B2_d0_HIGH_${schedule}`;
  const context=JSON.parse(fs.readFileSync(`${dir}/report.json`)).context;
  const source=JSON.parse(gunzipSync(fs.readFileSync(`${dir}/receipts_and_proofs.json.gz`)));
  const selected=source.transactions.filter(t=>!t.excluded_from_system_cost&&['approval','access','deployment','partition_setup','initial_publication','status_publication'].includes(t.category));
  for(let start=0;start<selected.length;start+=8){
    const batch=await Promise.all(selected.slice(start,start+8).map(async t=>{
      const tx=t.transaction,g=BigInt(t.receipt.gasUsed);
      const unsigned=ethers.Transaction.from({type:2,chainId:10,nonce:tx.nonce,gasLimit:tx.gasLimit,
        maxFeePerGas:price,maxPriorityFeePerGas:price-base,to:tx.to,value:tx.value,data:tx.data,accessList:tx.accessList??[]}).unsignedSerialized;
      const [dataFee,operatorFee]=await Promise.all([quote('getL1Fee',unsigned),quote('getOperatorFee',g)]);
      const execution=g*price,total=execution+dataFee+operatorFee;
      return {schedule,actor:t.actor,category:t.category,t:t.timestamp-(context.base-3600),gas:Number(g),
        source_tx_hash:t.receipt.hash,unsigned_sha256:createHash('sha256').update(unsigned).digest('hex'),
        execution_wei:String(execution),l1_data_wei:String(dataFee),operator_wei:String(operatorFee),total_wei:String(total)};
    }));rows.push(...batch);
  }
}
const meta={status:'PASS',kind:'read_only_fee_projection_not_OP_execution',endpoint,block,block_hash:head.hash,
  block_timestamp:parseInt(head.timestamp,16),retrieved_utc:new Date().toISOString(),effective_execution_price_wei:String(price),
  execution_price_source:'Archived 20 October 2026 OP block-weighted median within-block effective p50; not this block market price',
  oracle,fee_components:['execution gas proxy times 6661 wei','oracle getL1Fee(unsigned transaction)','oracle getOperatorFee(actual gas proxy)'],
  assumptions:['Original local-EVM gas used is assumed equal on OP; no OP execution was performed.',
    'Original to/data/value/nonce/gasLimit retained; type2 chainId=10 and common historical fee fields replace the local envelope.',
    'Same pinned historical oracle state applied to all 90-day events; no volatility or future-fee claim.',
    'Direct transactions only; paymaster bundle/user-operation costs remain unmeasured.'],
  input_hashes:Object.fromEntries(['weekly','control'].map(s=>{const f=`results/econ08_cohort/runs/N16_zk_B2_d0_HIGH_${s}/receipts_and_proofs.json.gz`;return[f,createHash('sha256').update(fs.readFileSync(f)).digest('hex')]})),rows};
fs.writeFileSync(path.join(out,'projection.json'),JSON.stringify(meta,null,2)+'\n');
fs.writeFileSync(path.join(out,'rpc_evidence.json'),JSON.stringify(raw,null,2)+'\n');
console.log(JSON.stringify({status:'PASS',transactions:rows.length,rpc_calls:requestId,block,block_hash:head.hash}));
