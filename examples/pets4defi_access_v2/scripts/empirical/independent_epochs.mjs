// Local defensive integration of four independent EVM signers and one cache epoch.
import assert from 'node:assert/strict';
import {randomBytes} from 'node:crypto';
import fs from 'node:fs';
import {ethers} from 'ethers';
import {network} from 'hardhat';
import {poseidonContract} from 'circomlibjs';
import * as snarkjs from 'snarkjs';
import solc from 'solc';
import {makeFixtures} from '../fixtures.mjs';

const outputFile='../../projects/pets4defi/econ08/empirical_v03/freshness_revision/results/issuer_epochs.json';
const files=['contracts/IndependentEpochPublisher.sol','contracts/BatchedPolicyRegistry.sol'];
const sources=Object.fromEntries(files.map(f=>[f,{content:fs.readFileSync(f,'utf8')}]));
const compiled=JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources,
  settings:{optimizer:{enabled:true,runs:200},evmVersion:'cancun',outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}}})));
assert.equal((compiled.errors??[]).filter(e=>e.severity==='error').length,0,JSON.stringify(compiled.errors));
const connection=await network.create({network:'l1',override:{allowBlocksWithSameTimestamp:true}});
async function run() {
  const rpc=connection.provider;
  const provider=new ethers.BrowserProvider(rpc,undefined,{cacheTimeout:-1});
  provider.pollingInterval=10;
  assert.equal((await provider.getNetwork()).chainId,31337n);
  const accounts=await Promise.all([0,1,2,3,4,5].map(i=>provider.getSigner(i)));
  const signers=accounts.slice(1,5), addresses=await Promise.all(signers.map(s=>s.getAddress()));
  const hasher=await new ethers.ContractFactory(poseidonContract.generateABI(2),poseidonContract.createCode(2),accounts[0]).deploy();
  await hasher.waitForDeployment();
  const now=(await provider.getBlock('latest')).timestamp, period=3600,lag=300;
  const fixture=await makeFixtures(addresses,now), hash=fixture.hash;
  const artifact=compiled.contracts[files[0]].IndependentEpochPublisher;
  const publisher=await new ethers.ContractFactory(artifact.abi,artifact.evm.bytecode.object,accounts[0]).deploy(addresses,
    await hasher.getAddress(),fixture.policyRoot,fixture.minTier,fixture.maxTTL,now,period,lag);
  await publisher.waitForDeployment();
  const gas=[],checks=[];
  function tree(leaves) {
    const levels=[leaves];
    while(levels.at(-1).length>1){
      const row=levels.at(-1);
      levels.push(Array.from({length:row.length/2},(_,i)=>hash(row[2*i],row[2*i+1])));
    }
    return {root:levels.at(-1)[0],siblings:index=>levels.slice(0,-1).map((r,l)=>r[(index>>l)^1])};
  }
  const leaf=c=>hash(hash(12,hash(11,c.secret)),hash(c.issuerId,hash(hash(c.tier,c.jurisdiction),hash(hash(c.notBefore,c.credentialExpiry),c.salt))));
  function roots(revoked) {
    return fixture.credentials.map((cs,i)=>{
      const leaves=Array(1024).fill(0n);
      leaves[0]=leaf(cs[0]);
      if(!(revoked && i===0)) leaves[1]=leaf(cs[1]);
      leaves[1023]=hash(71,BigInt('0x'+randomBytes(24).toString('hex')));
      return tree(leaves);
    });
  }
  const group=rs=>tree(rs.map((r,i)=>hash(hash(21,BigInt(addresses[i])),r.root)));
  async function submit(i,slot,root,stage) {
    const transaction=await publisher.connect(signers[i]).submit(slot,root);
    const receipt=await transaction.wait();
    gas.push({stage,position:i+1,gas:Number(receipt.gasUsed),to:transaction.to,data:transaction.data,local_tx_hash:transaction.hash});
  }
  async function jump(t){
    await rpc.request({method:'evm_setNextBlockTimestamp',params:[t]});
    await rpc.request({method:'evm_mine',params:[]});
  }
  const first=roots(false);
  for(let i=0;i<3;i++) await submit(i,now,first[i].root,'genesis');
  assert.equal(await publisher.registry(),ethers.ZeroAddress);
  await assert.rejects(publisher.connect(signers[0]).submit.staticCall(now,first[0].root));
  await assert.rejects(publisher.connect(accounts[5]).submit.staticCall(now,first[3].root));
  await submit(3,now,first[3].root,'genesis');
  const registry=new ethers.Contract(await publisher.registry(),compiled.contracts[files[1]].BatchedPolicyRegistry.abi,provider);
  assert.equal(await registry.registryRoot(),group(first).root);
  checks.push('four authenticated submissions before activation','unauthorized and duplicate calls rejected','on-chain subgroup root matches credential-tree calculation');
  const second=roots(false);
  assert(second.every((r,i)=>r.root!==first[i].root));
  await jump(now+period);
  await assert.rejects(publisher.connect(signers[0]).submit.staticCall(now+period,first[0].root));
  for(let i=0;i<4;i++)await submit(i,now+period,second[i].root,'empty');
  assert.equal(await registry.securityEpoch(),2n);
  const third=roots(true);assert(third.every((r,i)=>r.root!==second[i].root));
  await jump(now+2*period);
  for(let i=0;i<3;i++)await submit(i,now+2*period,third[i].root,'one_revocation');
  assert.equal(await registry.registryRoot(),group(second).root);
  await submit(3,now+2*period,third[3].root,'one_revocation');
  const combined=group(third);
  assert.equal(await registry.registryRoot(),combined.root);
  checks.push('all four issuer roots change on an empty epoch and an epoch with one revocation','same local root rejected','partial slot has no effect on active root');
  const input=fixture.inputFor({issuerIndex:0,credentialIndex:0,scope:7n,requestHash:9n,windowStart:BigInt(now),windowEnd:BigInt(now+600)});
  Object.assign(input,{registryRoot:String(combined.root),credentialSiblings:third[0].siblings(0).map(String),issuerSiblings:combined.siblings(0).map(String)});
  const {proof,publicSignals}=await snarkjs.groth16.fullProve(input,'build/access_js/access.wasm','build/access_final.zkey',undefined,undefined,{singleThread:true});
  assert(await snarkjs.groth16.verify(JSON.parse(fs.readFileSync('build/verification_key.json')),publicSignals,proof));
  assert.equal((await registry.acceptedRoot(combined.root,0,0))[0],true);
  const oldEpoch=await registry.securityEpoch();
  await jump(now+3*period);
  const fourth=roots(true);
  for(let i=0;i<3;i++)await submit(i,now+3*period,fourth[i].root,'missed');
  await jump(now+3*period+lag);
  assert.equal((await registry.securityDeadline(oldEpoch,0))[0],false);
  await jump(now+4*period);
  const recovered=roots(true);
  for(let i=0;i<4;i++)await submit(i,now+4*period,recovered[i].root,'recovery');
  assert.equal(await registry.securityEpoch(),oldEpoch+1n);
  checks.push('valid credential verified by existing Groth16 circuit after a revocation','incomplete slot fails closed at deadline','recovery requires four new contributions');
  const sum=stage=>gas.filter(r=>r.stage===stage).reduce((s,r)=>s+r.gas,0);
  fs.writeFileSync(outputFile,JSON.stringify({network:'local_evm',checks,gas,empty_epoch_gas:sum('empty'),changed_epoch_gas:sum('one_revocation'),usable_credential_slots_per_issuer:1023,private_padding_bits:192,padding_domain:71,proof_verified:true,public_signals:publicSignals,proof},null,2)+'\n');
  console.log(JSON.stringify({checks:checks.length,empty:sum('empty'),changed:sum('one_revocation')}));
}
try { await run(); } finally { await connection.close(); }
process.exit(0);
