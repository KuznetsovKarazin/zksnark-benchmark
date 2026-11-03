import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {performance} from 'node:perf_hooks';
import {network} from 'hardhat';
import {ethers} from 'ethers';
import solc from 'solc';
import {poseidonContract} from 'circomlibjs';
import * as snarkjs from 'snarkjs';
import {makeFixtures} from './fixtures.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
process.chdir(root);
const RUNS=Number(process.env.BENCH_RUNS??30);
assert(Number.isInteger(RUNS)&&RUNS>=1&&RUNS<=100,'BENCH_RUNS must be 1..100');
const POLICIES=[
  {id:'global',mode:0,delta_seconds:0,root_grace_seconds:0},
  {id:'security',mode:1,delta_seconds:0,root_grace_seconds:300},
  {id:'delay_300',mode:2,delta_seconds:300,root_grace_seconds:300},
  {id:'delay_3600',mode:2,delta_seconds:3600,root_grace_seconds:300},
];
const VARIANTS=['signed_direct','signed_cache','zk_direct','zk_cache'];
const FIELD=21888242871839275222246405745257275088548364400416034343698204186575808495617n;
const MASK=(1n<<248n)-1n;
const AMOUNT=ethers.parseUnits('100',18), BATCH_SIZE=8;
const events=[],failures=[],transactions=[],proofSamples=[],tests=[];
const json=v=>JSON.stringify(v,(_,x)=>typeof x==='bigint'?x.toString():x,2)+'\n';
const sha=v=>createHash('sha256').update(v).digest('hex');
const read=p=>fs.readFileSync(p,'utf8');
const write=(p,v)=>fs.writeFileSync(p,json(v));
const zk=v=>v.startsWith('zk'), cached=v=>v.endsWith('_cache');
fs.mkdirSync('results/policy_artifacts',{recursive:true});
const setup=JSON.parse(read('build/setup.json'));
for(const [k,p] of Object.entries({circuit_sha256:'circuits/access.circom',lock_sha256:'package-lock.json',
  zkey_sha256:'build/access_final.zkey',wasm_sha256:'build/access_js/access.wasm',
  verifier_sha256:'build/Verifier.sol',verification_key_sha256:'build/verification_key.json'}))
  assert.equal(setup[k],sha(fs.readFileSync(p)),`Stale setup: ${p}`);
const vkey=JSON.parse(read('build/verification_key.json'));
const files=['contracts/PolicyRegistry.sol','contracts/PolicyGate.sol','contracts/UncheckedDeposit.sol',
  'contracts/MockToken.sol','contracts/AdversarialToken.sol','build/Verifier.sol'];
const compilerSettings={optimizer:{enabled:true,runs:200},evmVersion:'cancun',
  outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}};
const compiled=JSON.parse(solc.compile(JSON.stringify({language:'Solidity',
  sources:Object.fromEntries(files.map(p=>[p,{content:read(p)}])),settings:compilerSettings})));
const errors=(compiled.errors??[]).filter(e=>e.severity==='error');
assert.equal(errors.length,0,errors.map(e=>e.formattedMessage).join('\n'));
const artifact=(file,name)=>compiled.contracts[file][name];
const verifierName=Object.keys(compiled.contracts['build/Verifier.sol']).find(n=>compiled.contracts['build/Verifier.sol'][n].evm.bytecode.object);
const types={Credential:[{name:'holder',type:'address'},{name:'id',type:'uint256'},
  {name:'policyVersion',type:'uint256'},{name:'validFrom',type:'uint64'},
  {name:'validUntil',type:'uint64'},{name:'eligible',type:'bool'}]};
const connection=await network.create('l1');
const rpc=connection.provider;
const provider=new ethers.BrowserProvider(rpc,undefined,{cacheTimeout:-1});provider.pollingInterval=10;
const signers=await Promise.all(Array.from({length:8},(_,i)=>provider.getSigner(i)));
const addresses=await Promise.all(signers.map(s=>s.getAddress()));
const owner=signers[0],holder=signers[5],attacker=signers[7],holderAddress=addresses[5];
const chainId=(await provider.getNetwork()).chainId;
const now=async()=>BigInt((await provider.getBlock('latest')).timestamp);
const fixtureTime=await now();
let fixtures=await makeFixtures(addresses.slice(0,4),fixtureTime);
let registry,token,verifier,hasher,unchecked;
const gates={};
const check=(name,extra={})=>tests.push({name,passed:true,...extra});
async function record(tx,policy,variant,event,run=0,extra={},measured=true){
  const receipt=await tx.wait();assert.equal(receipt.status,1,event);
  transactions.push({policy,variant,event,run,receipt:receipt.toJSON()});
  if(measured)events.push({chain:'l1',policy,variant,event,run,gas_used:Number(receipt.gasUsed),
    tx_hash:receipt.hash,evidence_status:'measured_local',...extra});
  return receipt;
}
async function deploy(file,name,args,policy,variant,event='deploy_gate',measured=true){
  const a=artifact(file,name),contract=await new ethers.ContractFactory(a.abi,a.evm.bytecode.object,owner).deploy(...args);
  await record(contract.deploymentTransaction(),policy,variant,event,0,{},measured);
  await contract.waitForDeployment();return contract;
}
const gateKey=(policy,variant)=>`${policy}/${variant}`;
const domain=()=>({name:'PETs4DeFiEligibility',version:'2',chainId,verifyingContract:registry.target});
let credential,signature;
async function makeProof(gate,{nonce,amount=AMOUNT,wallet=holderAddress,label='diagnostic',costSample=false,
  windowStart,windowEnd,fixture=fixtures,issuerIndex=0,credentialIndex=0}={}){
  nonce??=await gate.nonces(wallet);windowStart??=await now();windowEnd??=windowStart+fixtures.maxTTL;
  const rootValue=fixture.registryRoot;
  const scope=BigInt(ethers.keccak256(ethers.AbiCoder.defaultAbiCoder().encode(
    ['uint256','address','uint256'],[chainId,gate.target,1n])))%FIELD;
  assert.equal(await gate.computeScope(),scope);
  const request=await gate.computeRequestHashForRoot(rootValue,wallet,amount,nonce,windowStart,windowEnd);
  const rootRecord=await registry.roots(rootValue);
  const context=await gate.policyMode()===0n?await registry.publicationEpoch():rootRecord.securityEpoch;
  const action=ethers.keccak256(ethers.AbiCoder.defaultAbiCoder().encode(
    ['uint256','address','address','address','uint256','uint256'],
    [chainId,gate.target,wallet,await gate.token(),amount,nonce]));
  const independentRequest=BigInt(ethers.keccak256(ethers.AbiCoder.defaultAbiCoder().encode(
    ['bytes32','uint256','uint256','uint64','uint64'],[action,rootValue,context,windowStart,windowEnd])))&MASK;
  assert.equal(request,independentRequest,'action and accepted-root binding match independent encoding');
  const input=fixture.inputFor({scope,requestHash:request,windowStart,windowEnd,issuerIndex,credentialIndex});
  const start=performance.now();
  const {proof,publicSignals}=await snarkjs.groth16.fullProve(input,'build/access_js/access.wasm',
    'build/access_final.zkey',undefined,undefined,{singleThread:true});
  const proofMs=performance.now()-start,verifyStart=performance.now();
  assert.equal(await snarkjs.groth16.verify(vkey,publicSignals,proof),true);
  const verifyMs=performance.now()-verifyStart;
  const tuple=JSON.parse('['+await snarkjs.groth16.exportSolidityCallData(proof,publicSignals)+']');
  assert.equal(BigInt(publicSignals[1]),rootValue);assert.equal(BigInt(publicSignals[7]),request);
  const p={tuple,proof,publicSignals,nonce,proof_time_ms:proofMs,verification_time_ms:verifyMs,
    input_sha256:sha(json(input)),root:rootValue,windowStart,windowEnd};
  proofSamples.push({label,cost_sample:costSample,proof_time_ms:proofMs,verification_time_ms:verifyMs,
    proof,publicSignals,input_sha256:p.input_sha256});return p;
}
async function state(gate,asset=token,wallet=holderAddress){
  const result={nonce:await gate.nonces(wallet),deposit:await gate.deposits(wallet),
    holderBalance:await asset.balanceOf(wallet),gateBalance:await asset.balanceOf(gate.target)};
  if(gate.interface.hasFunction('caches'))result.cache=Array.from(await gate.caches(wallet));
  return result;
}
async function success(policy,variant,event,run=0,{gate,asset=token,proof,measured=true,extra={}}={}){
  gate??=variant==='unchecked'?unchecked:gates[gateKey(policy,variant)];
  const before=await state(gate,asset),cacheHit=event==='cache_hit'||event==='cache_hit_grace';
  const p=zk(variant)&&!cacheHit?(proof??await makeProof(gate,{nonce:before.nonce,label:`${policy}/${variant}/${event}/${run}`,costSample:measured})):null;
  let tx;
  if(variant==='unchecked')tx=await gate.deposit(AMOUNT,before.nonce);
  else if(cacheHit)tx=await gate.depositCached(AMOUNT,before.nonce);
  else if(zk(variant))tx=await gate.depositZK(p.tuple,AMOUNT,before.nonce);
  else tx=await gate.depositSigned(credential,signature,AMOUNT,before.nonce);
  const receipt=await record(tx,policy,variant,event,run,{proof_time_ms:p?.proof_time_ms??null,...extra},measured);
  const after=await state(gate,asset);
  assert.equal(after.nonce,before.nonce+1n);assert.equal(after.deposit,before.deposit+AMOUNT);
  assert.equal(after.holderBalance,before.holderBalance-AMOUNT);assert.equal(after.gateBalance,before.gateBalance+AMOUNT);
  check(`${policy}/${variant}/${event}/${run}: exact transfer and nonce`,{tx_hash:receipt.hash});return p;
}
function errorName(error,interfaces){
  if(error.revert?.name)return error.revert.name;
  const data=error.data??error.info?.error?.data;
  for(const i of interfaces){try{const parsed=i.parseError(typeof data==='string'?data:data?.data);if(parsed)return parsed.name;}catch{}}
  return null;
}
async function rejected(label,gate,method,args,{expected,asset=token,signer=holder,policy='diagnostic',variant='diagnostic',included=true,kind='rejected_action'}={}){
  const before=await state(gate,asset),wallet=await signer.getAddress();
  const beforeSender=await state(gate,asset,wallet);
  const boundNullifier=method==='depositZK'?BigInt(args[0][3][0]):null;
  const bindingBefore=boundNullifier===null?null:await gate.nullifierHolder(boundNullifier);
  let reason=null;
  try{await gate.connect(signer)[method].staticCall(...args);}
  catch(error){if(error.code!=='CALL_EXCEPTION')throw error;reason=errorName(error,[gate.interface,registry.interface,asset.interface]);}
  assert(reason,`${label}: static call unexpectedly accepted or undecoded`);
  if(expected)assert.equal(reason,expected,`${label}: wrong revert`);
  check(`${label}: preflight rejects`,{error:reason,phase:'static_call',gas_used:0});
  if(included){
    let receipt;
    try{const tx=await gate.connect(signer)[method](...args,{gasLimit:2000000n});await tx.wait();}
    catch(error){if(error.code!=='CALL_EXCEPTION'||!error.receipt)throw error;receipt=error.receipt;}
    assert(receipt&&receipt.status===0,`${label}: included reverted receipt missing`);
    failures.push({chain:'l1',policy,variant,kind,label,error:reason,gas_used:Number(receipt.gasUsed),tx_hash:receipt.hash,
      inclusion_timestamp:Number((await provider.getBlock(receipt.blockNumber)).timestamp),evidence_status:'measured_included_revert'});
    transactions.push({policy,variant,event:'included_revert',label,receipt:receipt.toJSON()});
  }
  assert.deepEqual(await state(gate,asset),before,`${label}: gate state changed`);
  assert.deepEqual(await state(gate,asset,wallet),beforeSender,`${label}: sender state changed`);
  if(boundNullifier!==null)assert.equal(await gate.nullifierHolder(boundNullifier),bindingBefore,`${label}: nullifier binding changed`);
  check(`${label}: state rollback`,{included_revert:included});return reason;
}
async function staticRegistryReject(label,method,args,signer,expected){
  let reason;
  try{await registry.connect(signer)[method].staticCall(...args);}catch(e){reason=errorName(e,[registry.interface]);}
  assert.equal(reason,expected,label);check(label,{phase:'static_call',error:reason});
}
async function mineAt(t){await rpc.request({method:'evm_setNextBlockTimestamp',params:[Number(t)]});await rpc.request({method:'evm_mine',params:[]});assert.equal(await now(),BigInt(t));}
async function nextAt(t){await rpc.request({method:'evm_setNextBlockTimestamp',params:[Number(t)]});}
function appendCredentials(index,count,saltBase){
  const offset=fixtures.credentials[index].length;
  assert(offset+count<=1024,'fixture capacity');
  for(let j=0;j<count;j++)fixtures.credentials[index].push({...fixtures.credentials[index][0],
    secret:1000000n+BigInt(saltBase+offset+j),salt:2000000n+BigInt(saltBase+offset+j)});
  return fixtures.setCredential(index,0,{});
}
let baseSnapshot;
async function isolated(label,fn){
  assert(await rpc.request({method:'evm_revert',params:[baseSnapshot]}));
  baseSnapshot=await rpc.request({method:'evm_snapshot',params:[]});
  fixtures=await makeFixtures(addresses.slice(0,4),fixtureTime);
  await fn();console.log(`PASS ${label}`);
}

try{
  hasher=await new ethers.ContractFactory(poseidonContract.generateABI(2),poseidonContract.createCode(2),owner).deploy();
  await record(hasher.deploymentTransaction(),'shared','shared','deploy_poseidon');await hasher.waitForDeployment();
  registry=await deploy('contracts/PolicyRegistry.sol','PolicyRegistry',
    [addresses[0],hasher.target,addresses.slice(0,4),fixtures.policyRoot,fixtures.minTier,fixtures.maxTTL],
    'shared','shared','deploy_registry');
  token=await deploy('contracts/MockToken.sol','MockToken',[holderAddress,ethers.parseUnits('10000000',18)],'shared','shared','deploy_token');
  verifier=await deploy('build/Verifier.sol',verifierName,[],'shared','shared','deploy_verifier');
  for(let i=0;i<4;i++)await record(await registry.connect(signers[i]).publishIssuerRoot(i,fixtures.issuerRoots[i],false),
    'shared','shared','issuer_root_initial',i,{issuer_index:i});
  assert.equal(await registry.registryRoot(),fixtures.registryRoot);check('hierarchical root matches independent fixture');
  unchecked=(await deploy('contracts/UncheckedDeposit.sol','UncheckedDeposit',[token.target],'none','unchecked')).connect(holder);
  await record(await token.connect(holder).transfer(unchecked.target,1n),'none','unchecked','bootstrap_token_balance');
  await record(await token.connect(holder).approve(unchecked.target,ethers.MaxUint256),'none','unchecked','approve');
  for(const policy of POLICIES)for(const variant of VARIANTS){
    const gate=(await deploy('contracts/PolicyGate.sol','PolicyGate',
      [registry.target,token.target,verifier.target,zk(variant),cached(variant),policy.mode,policy.delta_seconds,policy.root_grace_seconds],
      policy.id,variant)).connect(holder);
    gates[gateKey(policy.id,variant)]=gate;
    await record(await token.connect(holder).transfer(gate.target,1n),policy.id,variant,'bootstrap_token_balance');
    await record(await token.connect(holder).approve(gate.target,ethers.MaxUint256),policy.id,variant,'approve');
  }
  credential={holder:holderAddress,id:101n,policyVersion:await registry.policyVersion(),validFrom:fixtures.notBefore,
    validUntil:fixtures.credentialExpiry,eligible:true};
  signature=await signers[0].signTypedData(domain(),types,credential);
  assert.equal(await gates['security/signed_direct'].hashCredential(credential),ethers.TypedDataEncoder.hash(domain(),types,credential));
  baseSnapshot=await rpc.request({method:'evm_snapshot',params:[]});
  await success('none','unchecked','access_first');
  for(let run=1;run<=RUNS;run++)await success('none','unchecked','access_repeat',run);
  for(const policy of POLICIES)for(const variant of VARIANTS){
    await success(policy.id,variant,cached(variant)?'cache_register_first':'access_first');
    for(let run=1;run<=RUNS;run++)await success(policy.id,variant,cached(variant)?'cache_hit':'access_repeat',run);
    console.log(`${policy.id}/${variant}: first + ${RUNS} recurring actions`);
  }
  // A full refresh is a distinct measured operation. Independent signed caches
  // do not require it merely because an unrelated hidden root was changed.
  for(let run=1;run<=RUNS;run++){
    const start=performance.now(),rootValue=fixtures.refreshRoot(3,run);
    const treeMs=performance.now()-start;
    const receipt=await record(await registry.connect(signers[3]).publishIssuerRoot(3,rootValue,true),
      'shared','shared','issuer_security_update',run,{issuer_index:3,offchain_tree_update_ms:treeMs});
    const changedAt=BigInt((await provider.getBlock(receipt.blockNumber)).timestamp);
    // An accepted old epoch reads its invalidation timestamp; measure that
    // branch separately from a cache hit in the current security epoch.
    for(const policy of POLICIES.filter(p=>p.delta_seconds>0)){
      const gate=gates[gateKey(policy.id,'zk_cache')],authorization=await gate.caches(holderAddress);
      const currentEpoch=await registry.securityEpoch();
      assert(authorization.securityEpoch<currentEpoch,'grace sample must use an old cached epoch');
      const [accepted,deadline]=await registry.securityDeadline(authorization.securityEpoch,policy.delta_seconds);
      assert(accepted,'old cached epoch must remain accepted before the grace hit');
      assert.equal(deadline,changedAt+BigInt(policy.delta_seconds));
      await success(policy.id,'zk_cache','cache_hit_grace',run,{extra:{
        cached_security_epoch:authorization.securityEpoch,current_security_epoch:currentEpoch,
        security_invalidated_at:changedAt,exclusive_security_deadline:deadline}});
      const inclusion=await now();
      assert(inclusion<deadline&&inclusion<authorization.until,'grace hit must be included before both deadlines');
      assert.deepEqual(Array.from(await gate.caches(holderAddress)),Array.from(authorization),
        'a grace cache hit must not refresh or replace its saved authorization');
      Object.assign(events.at(-1),{inclusion_timestamp:inclusion,seconds_after_security_change:inclusion-changedAt});
      check(`${policy.id}/cache_hit_grace/${run}: accepted old epoch without refreshing authorization`);
    }
    await mineAt(changedAt+3601n);
    for(const policy of POLICIES){
      const zGate=gates[gateKey(policy.id,'zk_cache')];
      await rejected(`${policy.id}: old ZK cache rejected after security deadline`,zGate,'depositCached',
        [AMOUNT,await zGate.nonces(holderAddress)],{policy:policy.id,variant:'zk_cache',included:false});
      if(policy.id!=='global'){
        const sGate=gates[gateKey(policy.id,'signed_cache')];
        await sGate.depositCached.staticCall(AMOUNT,await sGate.nonces(holderAddress));
        check(`${policy.id}: unrelated hidden security update preserves signed credential status`);
      }
      for(const variant of ['signed_cache','zk_cache'])await success(policy.id,variant,'cache_reauthorize',run,
        {extra:{refresh_reason:variant==='signed_cache'&&policy.id!=='global'?'explicit_full_refresh_not_required_by_unrelated_root':'security_epoch_invalidated'}});
    }
  }
  // Actual batching: mutate eight new leaves off chain before one issuer-root
  // publication. Capacity remains bounded; this is not an N=1000 load test.
  for(let run=1;run<=RUNS;run++){
    const start=performance.now(),rootValue=appendCredentials(2,BATCH_SIZE,run*10000);
    const elapsed=performance.now()-start;
    await record(await registry.connect(signers[2]).publishIssuerRoot(2,rootValue,false),
      'shared','shared','batch_addition',run,{issuer_index:2,changed_leaves:BATCH_SIZE,
        root_publications:1,offchain_tree_update_ms:elapsed});
  }
  for(let j=0;j<Math.max(BATCH_SIZE,RUNS);j++){
    const start=performance.now(),rootValue=appendCredentials(1,1,900000+j);
    const treeMs=performance.now()-start;
    await record(await registry.connect(signers[1]).publishIssuerRoot(1,rootValue,false),
      'shared','shared','issuer_addition',j+1,{issuer_index:1,changed_leaves:1,
        root_publications:1,comparison_group:j<BATCH_SIZE?'eight_sequential_publications':'single_leaf_unit_replication',
        offchain_tree_update_ms:treeMs});
  }
  // Renewal/reissue replaces occupied slots rather than appending forever.
  // Replacing any hidden credential is declared as a security change; elapsed
  // expiry and correct issuer behavior remain off-chain responsibilities.
  for(let run=1;run<=RUNS;run++){
    const start=performance.now(),beforeCount=fixtures.credentials[2].length;
    for(let j=0;j<BATCH_SIZE;j++)Object.assign(fixtures.credentials[2][j],{
      secret:3000000n+BigInt(run*100+j),salt:4000000n+BigInt(run*100+j),
      credentialExpiry:fixtures.credentialExpiry+BigInt(run)*86400n,
    });
    const rootValue=fixtures.setCredential(2,0,{}),treeMs=performance.now()-start;
    assert.equal(fixtures.credentials[2].length,beforeCount,'replacement preserves occupied slot count');
    await record(await registry.connect(signers[2]).publishIssuerRoot(2,rootValue,true),
      'shared','shared','batch_security_update',run,{issuer_index:2,changed_leaves:BATCH_SIZE,
        root_publications:1,offchain_tree_update_ms:treeMs,replacement_kind:'existing_leaf_reissue'});
  }
  for(let run=1;run<=RUNS;run++)await record(await registry.connect(signers[0]).revokePublic(1000n+BigInt(run)),
    'shared','shared','public_id_revoke',run,{target:'unrelated_public_credential',scope:'signed_status_only'});

  await isolated('addition policy and in-flight proof',async()=>{
    const proofs={};
    for(const policy of POLICIES){
      for(const variant of ['signed_cache','zk_cache'])await success(policy.id,variant,'cache_register_first',0,{measured:false});
      proofs[policy.id]=await makeProof(gates[gateKey(policy.id,'zk_direct')],{label:`addition-race/${policy.id}`});
    }
    const rootValue=appendCredentials(3,1,500000);
    await (await registry.connect(signers[3]).publishIssuerRoot(3,rootValue,false)).wait();
    for(const variant of ['signed_cache','zk_cache'])await rejected(`global/${variant}: addition invalidates cache`,gates[`global/${variant}`],
      'depositCached',[AMOUNT,await gates[`global/${variant}`].nonces(holderAddress)],{policy:'global',variant,included:false});
    for(const policy of POLICIES.filter(p=>p.id!=='global'))for(const variant of ['signed_cache','zk_cache'])
      await success(policy.id,variant,'cache_hit',0,{measured:false});
    await rejected('global: queued proof fails after addition',gates['global/zk_direct'],'depositZK',
      [proofs.global.tuple,AMOUNT,0n],{policy:'global',variant:'zk_direct',kind:'stale_proof_after_addition'});
    const failedAttempt=failures.at(-1);
    const replacement=await makeProof(gates['global/zk_direct'],{label:'replacement-after-included-stale-proof'});
    await success('global','zk_direct','access_first',0,{proof:replacement,measured:false});
    Object.assign(failedAttempt,{wasted_proof_time_ms:proofs.global.proof_time_ms,
      replacement_proof_time_ms:replacement.proof_time_ms,
      replacement_tx_hash:transactions.at(-1).receipt.hash});
    for(const policy of POLICIES.filter(p=>p.id!=='global'))await success(policy.id,'zk_direct','access_first',0,
      {proof:proofs[policy.id],measured:false,extra:{root_state:'recent_superseded'}});
  });

  await isolated('public signed status is independent of hidden membership',async()=>{
    for(const variant of ['signed_cache','zk_cache'])await success('security',variant,'cache_register_first',0,{measured:false});
    const epoch=await registry.securityEpoch();
    await (await registry.connect(signers[0]).revokePublic(credential.id)).wait();
    assert.equal(await registry.securityEpoch(),epoch,'public-only ID revoke does not claim hidden-member removal');
    const signed=gates['security/signed_cache'];
    await rejected('public ID revoke rejects the signed cache',signed,'depositCached',
      [AMOUNT,await signed.nonces(holderAddress)],{policy:'security',variant:'signed_cache',included:false});
    await success('security','zk_cache','cache_hit',0,{measured:false});
    check('public-only revoke preserves selective hidden-membership authorization; combined revoke required for both');
  });

  await isolated('root grace exact boundary',async()=>{
    const gate=gates['security/zk_direct'],proof=await makeProof(gate,{label:'root-grace-boundary'});
    const receipt=await (await registry.connect(signers[3]).publishIssuerRoot(3,appendCredentials(3,1,600000),false)).wait();
    const supersededAt=BigInt((await provider.getBlock(receipt.blockNumber)).timestamp);
    await mineAt(supersededAt+299n);
    await gate.depositZK.staticCall(proof.tuple,AMOUNT,0n);check('old root accepted at tau-1');
    await mineAt(supersededAt+300n);
    await rejected('old root rejected exactly at tau',gate,'depositZK',[proof.tuple,AMOUNT,0n],
      {policy:'security',variant:'zk_direct',kind:'stale_proof_after_root_grace'});
  });

  for(const policy of POLICIES)await isolated(`${policy.id}: atomic credential revocation`,async()=>{
    const sg=gates[gateKey(policy.id,'signed_cache')],zg=gates[gateKey(policy.id,'zk_cache')];
    await success(policy.id,'signed_cache','cache_register_first',0,{measured:false});
    await success(policy.id,'zk_cache','cache_register_first',0,{measured:false});
    const oldProof=await makeProof(zg,{label:`revocation-queued/${policy.id}`});
    const newRoot=fixtures.removeCredential(0,0);
    const receipt=await (await registry.connect(signers[0]).revokeAndPublish(0,credential.id,newRoot)).wait();
    const revokedAt=BigInt((await provider.getBlock(receipt.blockNumber)).timestamp);
    const deadline=revokedAt+BigInt(policy.delta_seconds);
    if(policy.delta_seconds){
      // A queued old proof may be accepted during its root/security grace, but
      // any authorization it creates remains tied to the original deadline.
      await success(policy.id,'zk_cache','cache_reauthorize',0,{proof:oldProof,measured:false});
      const auth=await zg.caches(holderAddress);
      assert(auth.until<=deadline);check(`${policy.id}: old proof cannot extend its first revocation deadline`);
      await success(policy.id,'signed_cache','cache_reauthorize',0,{measured:false});
      assert((await sg.caches(holderAddress)).until<=deadline);
      check(`${policy.id}: signed full refresh during delay cannot extend revocation deadline`);
      await nextAt(deadline-1n);
      await success(policy.id,'zk_cache','cache_hit',0,{measured:false});
      assert.equal(await now(),deadline-1n);check(`${policy.id}: cached ZK accepted at Delta-1`);
      await sg.depositCached.staticCall(AMOUNT,await sg.nonces(holderAddress));
      check(`${policy.id}: cached signed accepted at Delta-1`);
      await mineAt(deadline);
    }
    for(const [variant,gate] of [['signed_cache',sg],['zk_cache',zg]])await rejected(`${policy.id}/${variant}: rejected at revocation deadline`,
      gate,'depositCached',[AMOUNT,await gate.nonces(holderAddress)],{policy:policy.id,variant,kind:'revoked_cached_access'});
    await rejected(`${policy.id}: signed full refresh cannot resurrect revoked ID`,sg,'depositSigned',
      [credential,signature,AMOUNT,await sg.nonces(holderAddress)],{policy:policy.id,variant:'signed_cache'});
    // The old proof's nonce is no longer current if it was accepted; query the
    // root-validity predicate separately to establish the deadline invariant.
    assert.equal((await registry.acceptedRoot(oldProof.root,policy.delta_seconds,policy.root_grace_seconds))[0],false);
    check(`${policy.id}: old root invalid at/after revocation deadline`);
  });

  for(const emergency of ['policy','policy_ttl','issuer'])await isolated(`${emergency}: emergency immediate`,async()=>{
    const policy='delay_3600';
    for(const variant of ['signed_cache','zk_cache'])await success(policy,variant,'cache_register_first',0,{measured:false});
    const proof=await makeProof(gates[`${policy}/zk_direct`],{label:`emergency-${emergency}`});
    if(emergency==='policy')await (await registry.updatePolicy(fixtures.policyRoot,3,fixtures.maxTTL)).wait();
    else if(emergency==='policy_ttl')await (await registry.updatePolicy(fixtures.policyRoot,fixtures.minTier,fixtures.maxTTL-1n)).wait();
    else await (await registry.disableIssuer(0)).wait();
    for(const variant of ['signed_cache','zk_cache'])await rejected(`${emergency}: ${variant} immediate rejection`,gates[`${policy}/${variant}`],
      'depositCached',[AMOUNT,await gates[`${policy}/${variant}`].nonces(holderAddress)],{policy,variant,included:false});
    await rejected(`${emergency}: queued proof rejected immediately`,gates[`${policy}/zk_direct`],'depositZK',[proof.tuple,AMOUNT,0n],
      {policy,variant:'zk_direct',kind:'emergency_invalidated_proof'});
  });

  await isolated('repeated security changes do not extend old acceptance',async()=>{
    const policy='delay_3600',gate=gates[`${policy}/zk_cache`];
    await success(policy,'zk_cache','cache_register_first',0,{measured:false});
    const oldEpoch=(await gate.caches(holderAddress)).securityEpoch;
    const receipt=await (await registry.connect(signers[3]).publishIssuerRoot(3,fixtures.refreshRoot(3,777),true)).wait();
    const first=BigInt((await provider.getBlock(receipt.blockNumber)).timestamp);
    await mineAt(first+100n);
    await (await registry.connect(signers[2]).publishIssuerRoot(2,fixtures.refreshRoot(2,778),true)).wait();
    assert.equal(await registry.securityInvalidatedAt(oldEpoch),first);
    await mineAt(first+3600n);
    await rejected('second security change cannot extend original cache deadline',gate,'depositCached',
      [AMOUNT,await gate.nonces(holderAddress)],{policy,variant:'zk_cache',included:false});
  });

  await isolated('context binding and controls',async()=>{
    await staticRegistryReject('untrusted issuer root update','publishIssuerRoot',[0,123n,false],attacker,'NotIssuer');
    await staticRegistryReject('root out of field','publishIssuerRoot',[0,FIELD,false],signers[0],'InvalidField');
    await staticRegistryReject('nonowner policy update','updatePolicy',[fixtures.policyRoot,3,60],attacker,'NotOwner');
    const gate=gates['security/zk_direct'],proof=await makeProof(gate,{label:'binding-controls'});
    const nonce=0n;
    await rejected('wrong amount cannot reuse proof',gate,'depositZK',[proof.tuple,AMOUNT+1n,nonce],{policy:'security',variant:'zk_direct'});
    await rejected('wrong wallet cannot reuse proof',gate,'depositZK',[proof.tuple,AMOUNT,nonce],{policy:'security',variant:'zk_direct',signer:attacker});
    const rebound=structuredClone(proof.tuple);
    rebound[3][7]=(await gate.computeRequestHashForRoot(proof.root,holderAddress,AMOUNT+1n,nonce,proof.windowStart,proof.windowEnd)).toString();
    assert.equal(await snarkjs.groth16.verify(vkey,[...proof.publicSignals.slice(0,7),rebound[3][7]],proof.proof),false);
    await rejected('public request is cryptographically bound',gate,'depositZK',[rebound,AMOUNT+1n,nonce],{policy:'security',variant:'zk_direct',expected:'InvalidProof'});
    const corrupted=structuredClone(proof.tuple);corrupted[0]=['0','0'];
    await rejected('malformed proof rejected',gate,'depositZK',[corrupted,AMOUNT,nonce],{policy:'security',variant:'zk_direct',expected:'InvalidProof'});
    await success('security','zk_direct','access_first',0,{proof,measured:false});
    await rejected('nonce replay rejected',gate,'depositZK',[proof.tuple,AMOUNT,nonce],{policy:'security',variant:'zk_direct',expected:'InvalidNonce'});
    await rejected('ungated zero amount rejected',unchecked,'deposit',[0n,0n],{variant:'unchecked',expected:'InvalidAmount'});
  });

  await isolated('cache expiry exact boundary',async()=>{
    for(const variant of ['signed_cache','zk_cache']){
      const policy='security',gate=gates[`${policy}/${variant}`];
      await success(policy,variant,'cache_register_first',0,{measured:false});
      const deadline=(await gate.caches(holderAddress)).until;
      await nextAt(deadline-1n);
      await success(policy,variant,'cache_hit',0,{measured:false});
      assert.equal(await now(),deadline-1n);check(`${variant}: accepted at expiry-1`);
      await mineAt(deadline);
      await rejected(`${variant}: rejected exactly at expiry`,gate,'depositCached',[AMOUNT,await gate.nonces(holderAddress)],
        {policy,variant,included:false,expected:'AuthorizationExpired'});
    }
  });

  await isolated('adversarial token rollback and reentry',async()=>{
    const bad=await deploy('contracts/AdversarialToken.sol','AdversarialToken',[holderAddress,ethers.parseUnits('100000',18)],'diagnostic','shared','deploy_adversarial_token',false);
    for(const variant of ['unchecked','signed_cache','zk_cache']){
      const gate=(variant==='unchecked'?await deploy('contracts/UncheckedDeposit.sol','UncheckedDeposit',[bad.target],'diagnostic',variant,'deploy_test_gate',false):
        await deploy('contracts/PolicyGate.sol','PolicyGate',[registry.target,bad.target,verifier.target,zk(variant),true,2,300,300],
          'diagnostic',variant,'deploy_test_gate',false)).connect(holder);
      await (await bad.connect(holder).approve(gate.target,ethers.MaxUint256)).wait();
      const proof=zk(variant)?await makeProof(gate,{label:'adversarial-token-proof'}):null;
      const method=variant==='unchecked'?'deposit':zk(variant)?'depositZK':'depositSigned';
      const args=variant==='unchecked'?[AMOUNT,0n]:zk(variant)?[proof.tuple,AMOUNT,0n]:[credential,signature,AMOUNT,0n];
      await (await bad.setFailureMode(1)).wait();
      await rejected(`${variant}: false token return rollback`,gate,method,args,{asset:bad,variant,expected:'TokenTransferFailed'});
      await (await bad.setFailureMode(2)).wait();
      await rejected(`${variant}: reverting token rollback`,gate,method,args,{asset:bad,variant,expected:'DeliberateTransferFailure'});
      await (await bad.setFailureMode(0)).wait();
      const reentry=gate.interface.encodeFunctionData(variant==='unchecked'?'deposit':'depositCached',[AMOUNT,0n]);
      await (await bad.setReentry(gate.target,reentry,true,false)).wait();
      const before=await state(gate,bad);
      await record(await gate[method](...args),'diagnostic',variant,'outer_action_with_blocked_reentry',0,{},false);
      const after=await state(gate,bad);
      assert.equal(await bad.lastReentrySuccess(),false);
      assert.equal(gate.interface.parseError(await bad.lastReentryResult()).name,'Reentrancy');
      assert.equal(after.nonce,before.nonce+1n);assert.equal(after.deposit,before.deposit+AMOUNT);
      assert.equal(after.holderBalance,before.holderBalance-AMOUNT);assert.equal(after.gateBalance,before.gateBalance+AMOUNT);
      check(`${variant}: blocked reentry with exactly one outer transfer`);
      await (await bad.setReentry(ethers.ZeroAddress,'0x',false,false)).wait();
    }
  });

  const sourceFiles=['package.json','package-lock.json','hardhat.config.js','circuits/access.circom',
    ...files.filter(p=>p!=='build/Verifier.sol'),'scripts/fixtures.mjs','scripts/policy_benchmark.mjs'];
  const sourceHashes=Object.fromEntries(sourceFiles.map(p=>[p,sha(fs.readFileSync(p))]));
  const metadata={recorded_at:new Date().toISOString(),source_sha:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),
    source_dirty:!!execFileSync('git',['status','--porcelain','--',...sourceFiles],{encoding:'utf8'}).trim(),
    source_files_sha256:sourceHashes,source_tree_sha256:sha(json(sourceHashes)),node:process.version,cpu:os.cpus()[0]?.model,
    platform:process.platform,arch:process.arch,logical_cpus:os.cpus().length,solc:solc.version(),compiler_settings:compilerSettings,
    setup,runs:RUNS,debug_run:RUNS!==30,chain:'l1',chain_id:chainId,hardfork:connection.networkConfig.hardfork,
    policies:POLICIES,variants:['unchecked',...VARIANTS],batch_size:BATCH_SIZE,
    measured_first_events:'one observation each',measured_recurring_events:`${RUNS} warmed successful actions per event/treatment`,
    cache_hit_sampling:'cache_hit uses the current security epoch; cache_hit_grace uses an unchanged old-epoch ZK authorization before its first invalidation deadline, separately for each positive-delay policy.',
    root_publication_work:'Fixed depth10 credential tree, four issuer slots; actual 8-leaf additions and occupied-slot replacements; not a population load test.',
    revocation_model:'Trusted issuer update declaration; opaque root does not enforce addition-only semantics. Public-ID revoke alone is signed-status only; revokeAndPublish pairs representations.',
    failure_model:'Included reverted transactions are measured separately; static preflight rejection incurs no chain gas. No observed network failure frequency is inferred.',
    cost_boundary:'Local L1 execution; fixture token/setup separate; issuer/witness services, actual user latency and full L2 fees unmeasured.',
    proof_boundary:'Single-thread fullProve plus separate strict verification; per-event server samples are not physical-device results.',
    addresses:{registry:registry.target,token:token.target,verifier:verifier.target,unchecked:unchecked.target,
      gates:Object.fromEntries(Object.entries(gates).map(([k,g])=>[k,g.target]))}};
  write('results/policy_measurements.json',{schema_version:1,metadata,events,failures});
  write('results/policy_tests.json',{source_tree_sha256:metadata.source_tree_sha256,passed:tests.length,failed:0,tests});
  write('results/policy_transactions.json',transactions);
  write('results/policy_proofs.json',{samples:proofSamples});
  for(const name of ['verification_key.json','Verifier.sol','setup.json'])fs.copyFileSync(`build/${name}`,`results/policy_artifacts/${name}`);
  console.log(`PASS ${tests.length} checks; ${events.length} measured events; ${failures.length} included reverts.`);
}catch(error){
  write('results/policy_debug_failure.json',{error:String(error),stack:error.stack,passed:tests.length,tests,events,failures});
  throw error;
}finally{await connection.close();}
process.exit(0);
