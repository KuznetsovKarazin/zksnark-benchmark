import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
import {network} from 'hardhat';
import {ethers} from 'ethers';
import solc from 'solc';
import {poseidonContract} from 'circomlibjs';
import * as snarkjs from 'snarkjs';
import {makeFixtures} from '../fixtures.mjs';
import {TTL} from './config.mjs';

export const json = x => JSON.stringify(x, (_, v) => typeof v === 'bigint' ? v.toString() : v, 2) + '\n';
export const hash = x => createHash('sha256').update(x).digest('hex');
export const AMOUNT = ethers.parseUnits('100', 18);
export const sourceFiles = [
  'package.json','package-lock.json','hardhat.config.js','circuits/access.circom',
  'contracts/PolicyRegistry.sol','contracts/PolicyGate.sol','contracts/MockToken.sol',
  'scripts/setup.mjs','scripts/fixtures.mjs',
  ...['config.mjs','test_config.mjs','harness.mjs','run.mjs','correctness.mjs','timing.mjs','check.py','proof_binding.py','verify_proofs.mjs','verify_transactions.mjs'].map(p=>'scripts/econ08/'+p),
];
export function errorName(error, interfaces) {
  if (error.revert?.name) return error.revert.name;
  const d = error.data ?? error.info?.error?.data;
  for (const i of interfaces) try { const e=i.parseError(typeof d==='string'?d:d?.data); if(e)return e.name; } catch {}
  return null;
}
const credentialTypes = {Credential:[
  {name:'holder',type:'address'},{name:'id',type:'uint256'},{name:'policyVersion',type:'uint256'},
  {name:'validFrom',type:'uint64'},{name:'validUntil',type:'uint64'},{name:'eligible',type:'bool'},
]};

export function prepare() {
  const setup = JSON.parse(fs.readFileSync('build/setup.json'));
  for (const [key, file] of Object.entries({circuit_sha256:'circuits/access.circom',lock_sha256:'package-lock.json',
    zkey_sha256:'build/access_final.zkey',wasm_sha256:'build/access_js/access.wasm',r1cs_sha256:'build/access.r1cs',
    verifier_sha256:'build/Verifier.sol',verification_key_sha256:'build/verification_key.json'})) {
    assert.equal(setup[key], hash(fs.readFileSync(file)), file);
  }
  const files=['contracts/PolicyRegistry.sol','contracts/PolicyGate.sol','contracts/MockToken.sol','build/Verifier.sol'];
  const settings={optimizer:{enabled:true,runs:200},evmVersion:'cancun',outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}};
  const compiled=JSON.parse(solc.compile(json({language:'Solidity',sources:Object.fromEntries(files.map(p=>[p,{content:fs.readFileSync(p,'utf8')}])),settings})));
  assert.equal((compiled.errors??[]).filter(e=>e.severity==='error').length,0,json(compiled.errors));
  const verifierName=Object.keys(compiled.contracts['build/Verifier.sol']).find(n=>compiled.contracts['build/Verifier.sol'][n].evm.bytecode.object);
  return {setup,settings,solc:solc.version(),compiled,verifierName,vk:JSON.parse(fs.readFileSync('build/verification_key.json'))};
}

// A fresh chain for every workload: LOW cannot warm the HIGH cache or storage.
// The only warm-up is one token unit in the measured gate, explicitly excluded
// from system costs along with the mock token deployment. It matches the
// pre-existing experiment's nonzero gate balance convention.
export async function context(env, data, {id, family='zk', groups=1, delta=0, purpose='workload', cohort=null}) {
  assert(['zk','signed'].includes(family)); assert([1,2,4].includes(groups));
  assert(family==='zk'||groups===1); assert([0,3600,86400].includes(delta));
  const connection=await network.create({network:'l1',override:{allowBlocksWithSameTimestamp:true}});
  const rpc=connection.provider, provider=new ethers.BrowserProvider(rpc,undefined,{cacheTimeout:-1}); provider.pollingInterval=10;
  const signers=await Promise.all(Array.from({length:cohort?9:8},(_,i)=>provider.getSigner(i)));
  const addresses=await Promise.all(signers.map(s=>s.getAddress()));
  const owner=signers[0], holder=signers[5], wallet=addresses[5];
  const base=BigInt((await provider.getBlock('latest')).timestamp)+3600n;
  const fixtures=[];
  for(let g=0;g<groups;g++) {
    const f=await makeFixtures(addresses.slice(0,4),base);
    if(cohort) cohort.populate(f);
    for(let i=0;i<4;i++) if(Math.floor(i/(4/groups))!==g) f.setIssuerDisabled(i);
    fixtures.push(f);
  }
  const fixture=fixtures[0];
  const pin=async t=>rpc.request({method:'evm_setNextBlockTimestamp',params:[Number(t)]});
  const advance=async t=>{await pin(t);await rpc.request({method:'evm_mine',params:[]});};
  const check=(name,extra={})=>data.checks.push({scenario:id,name,passed:true,...extra});
  async function receipt(tx, category, actor, extra={}, expectedStatus=1) {
    let r; try {r=await tx.wait();} catch(e) {r=e.receipt; if(!r)throw e;}
    assert.equal(r.status,expectedStatus);
    const block=await provider.getBlock(r.blockNumber);
    data.transactions.push({scenario:id,purpose,category,actor,...extra,timestamp:block.timestamp,
      calldata_bytes:(tx.data.length-2)/2,receipt:r.toJSON(),transaction:tx.toJSON()});
    return r;
  }
  async function deploy(file,name,args=[],extra={}) {
    const a=env.compiled.contracts[file][name];
    const c=await new ethers.ContractFactory(a.abi,a.evm.bytecode.object,owner).deploy(...args);
    await receipt(c.deploymentTransaction(),'deployment','operator',{component:name,...extra});
    await c.waitForDeployment(); return c;
  }
  const hasher=await new ethers.ContractFactory(poseidonContract.generateABI(2),poseidonContract.createCode(2),owner).deploy();
  await receipt(hasher.deploymentTransaction(),'deployment','operator',{component:'Poseidon'}); await hasher.waitForDeployment();
  const registries=[];
  for(let g=0;g<groups;g++) {
    const reg=await deploy('contracts/PolicyRegistry.sol','PolicyRegistry',[addresses[0],hasher.target,addresses.slice(0,4),fixture.policyRoot,fixture.minTier,fixture.maxTTL],{group:g});
    registries.push(reg);
    for(let i=0;i<4;i++) if(Math.floor(i/(4/groups))!==g) {
      await receipt(await reg.disableIssuer(i),'partition_setup','operator',{group:g,issuer:i});
      await assert.rejects(reg.connect(signers[i]).publishIssuerRoot.staticCall(i,fixtures[g].issuerRoots[i],false),e=>errorName(e,[reg.interface])==='InactiveIssuer');
      check('excluded_issuer_cannot_publish',{group:g,issuer:i,method:'static_call'});
    }
  }
  const registry=registries[0];
  const token=await deploy('contracts/MockToken.sol','MockToken',[wallet,ethers.parseUnits('10000000',18)],{excluded_from_system_cost:true});
  // No diagnostic signed gate or verifier is silently charged to a ZK group.
  const verifier=family==='zk'?await deploy('build/Verifier.sol',env.verifierName):null;
  for(let i=0;i<4;i++) {
    const group=Math.floor(i/(4/groups));
    await receipt(await registries[group].connect(signers[i]).publishIssuerRoot(i,fixtures[group].issuerRoots[i],false),
      'initial_publication',`issuer_${i}`,{group,issuer:i});
  }
  for(let g=0;g<groups;g++) assert.equal(await registries[g].registryRoot(),fixtures[g].registryRoot);
  const gates=[];
  for(let g=0;g<groups;g++) gates.push((await deploy('contracts/PolicyGate.sol','PolicyGate',
    [registries[g].target,token.target,verifier?.target??ethers.ZeroAddress,family==='zk',true,delta===0?1:2,delta,0],{group:g})).connect(holder));
  const chainId=(await provider.getNetwork()).chainId;
  const domain={name:'PETs4DeFiEligibility',version:'2',chainId,verifyingContract:registry.target};
  const holders=[];
  const groupOf=issuer=>Math.floor(issuer/(4/groups));
  for(let group=0;group<(cohort?groups:1);group++) {
    await receipt(await token.connect(holder).transfer(gates[group].target,1n),'fixture_bootstrap','holder',
      {excluded_from_system_cost:true,...(cohort?{group}:{})});
  }
  for(let issuer=0;issuer<(cohort?4:1);issuer++) {
    const signer=signers[5+issuer], address=addresses[5+issuer], group=groupOf(issuer);
    const g=gates[group].connect(signer), f=fixtures[group];
    const actor=cohort?`holder_${issuer}`:'holder';
    if(issuer>0) await receipt(await token.connect(holder).transfer(address,AMOUNT*100n+1n),
      'fixture_funding',actor,{excluded_from_system_cost:true});
    await receipt(await token.connect(signer).approve(g.target,ethers.MaxUint256),'approval',actor);
    const credential={holder:address,id:101n+BigInt(issuer),policyVersion:1n,
      validFrom:f.notBefore,validUntil:f.credentialExpiry,eligible:true};
    const signature=await signers[issuer].signTypedData(domain,credentialTypes,credential);
    holders.push({issuer,address,g,f,credential,signature,actor,group});
  }
  const {g:gate,credential,signature}=holders[0];
  const state=async(g=gate,w=wallet,reg=registry)=>({nonce:await g.nonces(w),deposit:await g.deposits(w),
    holderBalance:await token.balanceOf(w),gateBalance:await token.balanceOf(g.target),
    cache:Array.from(await g.caches(w)),securityEpoch:await reg.securityEpoch()});
  async function proof(t,{g=gate,f=fixture,w=wallet,issuerIndex=0,credentialIndex=0,inputOverrides={}}={}) {
    const nonce=await g.nonces(w),end=t+BigInt(TTL)<f.credentialExpiry?t+BigInt(TTL):f.credentialExpiry;
    const scope=await g.computeScope();
    const requestHash=await g.computeRequestHashForRoot(f.registryRoot,w,AMOUNT,nonce,t,end);
    const input=f.inputFor({issuerIndex,credentialIndex,scope,requestHash,windowStart:t,windowEnd:end,...inputOverrides});
    const start=performance.now();
    const {proof:pr,publicSignals}=await snarkjs.groth16.fullProve(input,'build/access_js/access.wasm','build/access_final.zkey',undefined,undefined,{singleThread:true});
    const proof_ms=performance.now()-start;
    assert.equal(await snarkjs.groth16.verify(env.vk,publicSignals,pr),true);
    const tuple=JSON.parse('['+await snarkjs.groth16.exportSolidityCallData(pr,publicSignals)+']');
    const index=data.proofs.length;
    data.proofs.push({scenario:id,purpose,index,nonce,t,input,proof:pr,publicSignals,proof_ms});
    return {tuple,nonce,proof_ms,index};
  }
  async function deposit(t,{expectedEvent=null,index=null,issuer=0}={}) {
    const {g,f,address,actor,group,credential,signature}=holders[issuer], reg=registries[group];
    await advance(t); const before=await state(g,address,reg); let hit=true,reason=null;
    try {await g.depositCached.staticCall(AMOUNT,before.nonce);}
    catch(e) {reason=errorName(e,[g.interface,reg.interface]);assert(reason);hit=false;}
    const event=hit?'hit':before.nonce===0n?'first':'reauthorize';
    if(expectedEvent!==null)assert.equal(event,expectedEvent,`${id}/${issuer}/${index}`);
    const pr=family==='zk'&&!hit?await proof(t,{g,f,w:address,issuerIndex:issuer}):null;
    await pin(t);
    const tx=hit?await g.depositCached(AMOUNT,before.nonce)
      :family==='zk'?await g.depositZK(pr.tuple,AMOUNT,before.nonce)
        :await g.depositSigned(credential,signature,AMOUNT,before.nonce);
    const holderFields=cohort?{holder_issuer:issuer,group}:{};
    const r=await receipt(tx,'access',actor,{event,index,proof_index:pr?.index??null,...holderFields});
    const after=await state(g,address,reg);
    assert.equal(after.nonce,before.nonce+1n);assert.equal(after.deposit,before.deposit+AMOUNT);
    assert.equal(after.holderBalance,before.holderBalance-AMOUNT);assert.equal(after.gateBalance,before.gateBalance+AMOUNT);
    assert.equal(BigInt((await provider.getBlock(r.blockNumber)).timestamp),t);
    if(!hit)assert.equal(after.cache[0],t+BigInt(TTL)<f.credentialExpiry?t+BigInt(TTL):f.credentialExpiry);
    const row={scenario:id,purpose,index,at:Number(t-base),event,reason,gas:Number(r.gasUsed),tx_hash:r.hash,
      proof_index:pr?.index??null,proof_ms:pr?.proof_ms??null,before,after,...holderFields};
    data.accesses.push(row); return row;
  }
  async function revoke(issuer,credentialIndex,t,{own=false}={}) {
    const group=Math.floor(issuer/(4/groups)),reg=registries[group],f=fixtures[group];
    const oldEpochs=await Promise.all(registries.map(r=>r.securityEpoch()));
    const publicId=own?credential.id:1000n+BigInt(issuer*100+credentialIndex);
    await advance(t);const newRoot=f.removeCredential(issuer,credentialIndex); await pin(t);
    await receipt(await reg.connect(signers[issuer]).revokeAndPublish(issuer,publicId,newRoot),
      'status_publication',`issuer_${issuer}`,{issuer,credential:credentialIndex,public_id:publicId,group,own});
    for(let g=0;g<groups;g++) {
      assert.equal(await registries[g].registryRoot(),fixtures[g].registryRoot);
      assert.equal(await registries[g].securityEpoch(),oldEpochs[g]+(g===group?1n:0n));
    }
  }
  async function reject(name,method,args,t,expected,{g=gate,w=wallet}={}) {
    await advance(t); const before=await state(g,w); let reason=null;
    try {await g[method].staticCall(...args);} catch(e) {reason=errorName(e,[g.interface,registry.interface]);}
    assert.equal(reason,expected,name); await pin(t);
    const tx=await g[method](...args,{gasLimit:1200000});
    const r=await receipt(tx,'rejected','holder',{name,reason},0);
    const after=await state(g,w);assert.deepEqual(after,before,name);
    check(name,{method:'transaction',reason,tx_hash:r.hash,before,after});
    return r;
  }
  data.contexts.push({id,purpose,family,groups,delta,base:Number(base),wallet,chain_id:Number(chainId),
    registries:registries.map(r=>r.target),gates:gates.map(g=>g.target),token:token.target,
    verifier:verifier?.target??null,holder_issuer:0,holder_credential:0,population:cohort?.population??8,
    ...(cohort?{holders:holders.map(({issuer,address,group})=>({issuer,address,group}))}:{})});
  return {id,family,groups,delta,connection,rpc,provider,base,wallet,addresses,signers,holder,fixture,fixtures,
    registry,registries,gate,gates,token,credential,signature,domain,state,pin,advance,receipt,proof,deposit,revoke,reject,check};
}
