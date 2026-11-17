// Local integration and optional public-testnet execution of the combined-root adapter.
// All secrets stay in memory. Public runs use an explicitly supplied funded signer.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import zlib from 'node:zlib';
import {network} from 'hardhat';
import {ethers} from 'ethers';
import solc from 'solc';
import * as snarkjs from 'snarkjs';
import {makeFixtures} from '../fixtures.mjs';
import {extract} from './extractor.mjs';

const opts=Object.fromEntries(process.argv.slice(2).map(x=>{const i=x.indexOf('=');return i<0?[x.slice(2),true]:[x.slice(2,i),x.slice(i+1)];}));
const live=Boolean(opts.broadcast),N=Number(opts.holders??32);
assert([4,32,128].includes(N),'holders must be 4, 32, or 128');
const out=path.resolve(opts.out??`../../projects/pets4defi/econ08/empirical_v03/results/evm_N${N}`);
fs.mkdirSync(out,{recursive:true});
const json=x=>JSON.stringify(x,(_,v)=>typeof v==='bigint'?v.toString():v,2)+'\n';
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const files=['contracts/BatchedPolicyRegistry.sol','contracts/PolicyGate.sol','contracts/MockToken.sol','build/Verifier.sol'];
const setup=JSON.parse(fs.readFileSync('build/setup.json'));
for(const [key,file] of Object.entries({circuit_sha256:'circuits/access.circom',lock_sha256:'package-lock.json',
  zkey_sha256:'build/access_final.zkey',wasm_sha256:'build/access_js/access.wasm',verifier_sha256:'build/Verifier.sol'})) assert.equal(sha(fs.readFileSync(file)),setup[key],file);
const settings={optimizer:{enabled:true,runs:200},evmVersion:'cancun',outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}};
const compiled=JSON.parse(solc.compile(json({language:'Solidity',sources:Object.fromEntries(files.map(f=>[f,{content:fs.readFileSync(f,'utf8')}])),settings})));
const errors=(compiled.errors??[]).filter(x=>x.severity==='error');assert.equal(errors.length,0,json(errors));
const contracts=compiled.contracts;
const verifierName=Object.keys(contracts['build/Verifier.sol']).find(n=>contracts['build/Verifier.sol'][n].evm.bytecode.object);
let connection,rpc,provider,owner;
if(live) {
  assert(process.env.ECON08_TESTNET_RPC,'Set ECON08_TESTNET_RPC');
  assert(process.env.ECON08_TESTNET_PRIVATE_KEY,'A funded testnet signer is required; never paste a key in a chat');
  provider=new ethers.JsonRpcProvider(process.env.ECON08_TESTNET_RPC,undefined,{cacheTimeout:-1});
  owner=new ethers.Wallet(process.env.ECON08_TESTNET_PRIVATE_KEY,provider);
} else {
  connection=await network.create({network:'l1',override:{allowBlocksWithSameTimestamp:true}});
  rpc=connection.provider;provider=new ethers.BrowserProvider(rpc,undefined,{cacheTimeout:-1});
  owner=await provider.getSigner(0);
}
provider.pollingInterval=live?1000:10;
const chainId=(await provider.getNetwork()).chainId;
assert(live?[84532n,11155420n].includes(chainId):chainId===31337n,'Refusing unexpected chain / mainnet');
const checks=[],records=[],truth=[];
const check=name=>checks.push(name);
const record=async(tx,expected=1)=>{
  let receipt;try{receipt=await tx.wait();}catch(e){receipt=e.receipt;if(!receipt)throw e;}
  assert.equal(receipt.status,expected);
  const block=await provider.getBlock(receipt.blockNumber);
  // Re-fetch the mined transaction: a Wallet's original TransactionResponse can
  // still have null blockHash/blockNumber even after wait() returns a receipt.
  const rawReceipt=await provider.send('eth_getTransactionReceipt',[tx.hash]);
  const rawTx=await provider.send('eth_getTransactionByHash',[tx.hash]);
  records.push({transaction:rawTx,receipt:rawReceipt,block:{number:block.number,hash:block.hash,timestamp:block.timestamp}});
  return receipt;
};
const deploy=async(file,name,args)=>{
  const a=contracts[file][name],c=await new ethers.ContractFactory(a.abi,a.evm.bytecode.object,owner).deploy(...args);
  await record(c.deploymentTransaction());await c.waitForDeployment();return c;
};
const now=()=>provider.getBlock('latest').then(b=>b.timestamp);
const advance=async(t)=>{
  if(live) {
    while(await now()<t) await new Promise(resolve=>setTimeout(resolve,1000));
  } else {
    await rpc.request({method:'evm_setNextBlockTimestamp',params:[t]});await rpc.request({method:'evm_mine',params:[]});
  }
};
const signerAddresses=live?Array.from({length:4},()=>ethers.Wallet.createRandom().address):await Promise.all([0,1,2,3].map(async i=>(await provider.getSigner(i)).getAddress()));
const f=await makeFixtures(signerAddresses,await now());
const per=N/4;
for(let i=0;i<4;i++) {
  const base={...f.credentials[i][0]};
  f.credentials[i].splice(0,f.credentials[i].length,...Array.from({length:per+1},(_,j)=>({...base,secret:100000n+BigInt(i*1000+j),salt:200000n+BigInt(i*1000+j)})));
  f.setCredential(i,0,{});
}
const wallets=Array.from({length:N},()=>ethers.Wallet.createRandom().connect(provider));
const feeData=await provider.getFeeData();
const walletFunding=live?(2000000n*(feeData.maxFeePerGas??1000000n)*4n+100000000000000n):ethers.parseEther('1');
const fundingCap=ethers.parseEther(String(opts['max-testeth']??'0.05'));
if(live) {
  assert(walletFunding*BigInt(N)<fundingCap,'Funding estimate exceeds explicit testETH cap');
  assert(await provider.getBalance(await owner.getAddress())>walletFunding*BigInt(N)+ethers.parseEther('0.002'),'Insufficient testETH including operator reserve');
}
const verifier=await deploy('build/Verifier.sol',verifierName,[]);
const token=await deploy('contracts/MockToken.sol','MockToken',[await owner.getAddress(),BigInt(N)*1000n]);
// Live proof generation may be slow; allow a 15-minute publication slot. The live
// run is a compressed functional demonstration, not a replay of 90 real days.
const P=Number(opts.period??(live?900:3600)),L=Number(opts.lag??(live?180:300));
assert(Number.isInteger(P)&&Number.isInteger(L)&&L>0&&L<P,'Require 0 < lag < period');
const cutoff=await now();
const registry=await deploy('contracts/BatchedPolicyRegistry.sol','BatchedPolicyRegistry',
  [await owner.getAddress(),f.registryRoot,f.policyRoot,f.minTier,86400,P,L,cutoff]);
const gate=await deploy('contracts/PolicyGate.sol','PolicyGate',[registry.target,token.target,verifier.target,true,true,1,0,0]);
assert.equal(await gate.policyMode(),1n);assert.equal(await gate.deltaSeconds(),0n);assert.equal(await gate.rootGraceSeconds(),0n);check('supported_gate_configuration');
const config={chainId:chainId.toString(),gates:[gate.target],registries:[registry.target],chainType:live?'op':'l1',operatorFeeModel:'unknown'};
const manifest={mode:live?'PUBLIC_TESTNET':'LOCAL_EVM',chain_id:chainId.toString(),holders:N,issuers:4,period_seconds:P,lag_seconds:L,
  addresses:{registry:registry.target,gate:gate.target,verifier:verifier.target,token:token.target},
  code_hashes:Object.fromEntries(await Promise.all([registry,gate,verifier,token].map(async c=>[c.target,ethers.keccak256(await provider.getCode(c.target))]))),
  source_sha256:Object.fromEntries(files.map(file=>[file,sha(fs.readFileSync(file))])),setup,
  gas_currency:live?'testETH; not a mainnet economic price':'local-EVM gas units',
  limitations:['Synthetic credentials and accesses','Trusted complete private issuer feed','Four issuer slots','Demonstration phase-2 setup; not production-safe'],extractor_config:config};
fs.writeFileSync(path.join(out,'deployment.json'),json(manifest));
for(const w of wallets) {
  await record(await owner.sendTransaction({to:w.address,value:walletFunding}));
  await record(await token.transfer(w.address,1000));
  await record(await token.connect(w).approve(gate.target,ethers.MaxUint256));
}
const vk=JSON.parse(fs.readFileSync('build/verification_key.json'));
const proof=async(index)=>{
  const w=wallets[index],t=BigInt(await now()),end=t+86400n,nonce=await gate.nonces(w.address);
  const input=f.inputFor({issuerIndex:Math.floor(index/per),credentialIndex:index%per,
    scope:await gate.computeScope(),requestHash:await gate.computeRequestHashForRoot(f.registryRoot,w.address,1,nonce,t,end),windowStart:t,windowEnd:end});
  const {proof:pr,publicSignals}=await snarkjs.groth16.fullProve(input,'build/access_js/access.wasm','build/access_final.zkey',undefined,undefined,{singleThread:true});
  assert(await snarkjs.groth16.verify(vk,publicSignals,pr));
  return {tuple:JSON.parse('['+await snarkjs.groth16.exportSolidityCallData(pr,publicSignals)+']'),nonce};
};
const full=async(index)=>{const pr=await proof(index),tx=await gate.connect(wallets[index]).depositZK(pr.tuple,1,pr.nonce);await record(tx);truth.push({hash:tx.hash,kind:'full_zk'});};
const hit=async(index)=>{const tx=await gate.connect(wallets[index]).depositCached(1,await gate.nonces(wallets[index].address));await record(tx);truth.push({hash:tx.hash,kind:'hit'});};
for(let i=0;i<N;i++){await full(i);await hit(i);if(i%8===0)console.log(json({phase:'initial',done:i+1,holders:N}).trim());}
check('real_groth16_proofs_all_issuers');check('cached_access_all_holders');
const queued=await proof(0);
await assert.rejects(registry.connect(wallets[0]).publishCombinedRoot.staticCall(f.registryRoot,cutoff+P));check('unauthorized_publisher_rejected');
await assert.rejects(registry.publishCombinedRoot.staticCall(f.registryRoot,cutoff));check('duplicate_slot_rejected');
for(let i=0;i<4;i++)f.removeCredential(i,per); // Private revocation of four unused test credentials.
await advance(cutoff+P);
await record(await registry.publishCombinedRoot(f.registryRoot,cutoff+P));
await assert.rejects(gate.connect(wallets[0]).depositCached.staticCall(1,await gate.nonces(wallets[0].address)));check('batch_invalidates_existing_cache');
await assert.rejects(gate.connect(wallets[0]).depositZK.staticCall(queued.tuple,1,queued.nonce));check('queued_old_root_proof_rejected');
for(let i=0;i<N;i++) await full(i);
check('reauthorization_with_unchanged_gate_and_circuit');
assert.equal((await registry.acceptedRoot(f.registryRoot,1,0))[0],false);check('extra_grace_rejected');
if(!live) {
  const queuedSameRoot=await proof(0);
  await advance(cutoff+2*P);
  await record(await registry.publishCombinedRoot(f.registryRoot,cutoff+2*P));check('unchanged_root_heartbeat_allowed');
  await assert.rejects(gate.connect(wallets[0]).depositCached.staticCall(1,await gate.nonces(wallets[0].address)));check('unchanged_root_heartbeat_invalidates_cache');
  await assert.rejects(gate.connect(wallets[0]).depositZK.staticCall(queuedSameRoot.tuple,1,queuedSameRoot.nonce));check('queued_same_root_old_epoch_proof_rejected');
  await full(0);
  await advance(cutoff+3*P+L-1);await gate.connect(wallets[0]).depositCached.staticCall(1,await gate.nonces(wallets[0].address));check('cache_valid_before_freshness_boundary');
  await advance(cutoff+3*P+L);
  await assert.rejects(gate.connect(wallets[0]).depositCached.staticCall(1,await gate.nonces(wallets[0].address)));check('cache_rejected_at_freshness_boundary');
  assert.equal((await registry.acceptedRoot(f.registryRoot,0,0))[0],false);check('root_rejected_at_freshness_boundary');
  await registry.publishCombinedRoot.staticCall(f.registryRoot,cutoff+3*P);check('publication_allowed_at_inclusive_lag_boundary');
  await advance(cutoff+3*P+L+1);
  await assert.rejects(registry.publishCombinedRoot.staticCall(f.registryRoot,cutoff+3*P));check('late_publication_rejected');
}
fs.writeFileSync(path.join(out,'public_records.json.gz'),zlib.gzipSync(json(records)));
const extracted=records.map(r=>extract(r,config));
const byHash=new Map(extracted.map(r=>[r.tx_hash,r]));
assert(truth.every(x=>byHash.get(x.hash)?.kind===x.kind));check('public_only_extractor_matches_all_accesses');
assert(extracted.filter(x=>x.kind==='publication').every(x=>x.public_issuer_index===null));check('no_issuer_index_in_batch_event');
const report={...manifest,status:'PASS',checks,transactions:records.length,accesses:truth.length,mismatches:0,
  gas_by_kind:Object.fromEntries(['full_zk','hit','publication'].map(k=>[k,extracted.filter(x=>x.kind===k).map(x=>Number(x.fees.gas_used))])),
  public_testnet_complete:live};
fs.writeFileSync(path.join(out,'report.json'),json(report));
fs.writeFileSync(path.join(out,'public_records.json.gz'),zlib.gzipSync(json(records)));
fs.writeFileSync(path.join(out,'extracted.json'),json(extracted));
console.log(json({status:'PASS',holders:N,accesses:truth.length,transactions:records.length,checks:checks.length,live}).trim());
await connection?.close();process.exit(0);
