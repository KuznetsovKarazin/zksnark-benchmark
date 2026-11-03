// Bounded end-to-end validation for the private eligibility article.
// Synthetic credentials only. Original contracts/circuit and archived results are unchanged.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {performance} from 'node:perf_hooks';
import {gzipSync} from 'node:zlib';
import {network} from 'hardhat';
import {ethers} from 'ethers';
import solc from 'solc';
import {poseidonContract} from 'circomlibjs';
import * as snarkjs from 'snarkjs';
import {makeFixtures} from './fixtures.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');process.chdir(root);
const out=path.resolve(process.env.VALIDATION_OUT??'results/revocation_validation');fs.mkdirSync(out,{recursive:true});
const DAY=86400n,TTL=30n*DAY,AMOUNT=ethers.parseUnits('100',18);
const json=x=>JSON.stringify(x,(_,v)=>typeof v==='bigint'?v.toString():v,2)+'\n';
const hash=x=>createHash('sha256').update(x).digest('hex');
const read=p=>fs.readFileSync(p,'utf8');
const setup=JSON.parse(read('build/setup.json'));
for(const [k,p] of Object.entries({circuit_sha256:'circuits/access.circom',lock_sha256:'package-lock.json',zkey_sha256:'build/access_final.zkey',wasm_sha256:'build/access_js/access.wasm',verifier_sha256:'build/Verifier.sol',verification_key_sha256:'build/verification_key.json'}))assert.equal(setup[k],hash(fs.readFileSync(p)),p);
const vk=JSON.parse(read('build/verification_key.json'));
const files=['contracts/PolicyRegistry.sol','contracts/PolicyGate.sol','contracts/MockToken.sol','build/Verifier.sol'];
const settings={optimizer:{enabled:true,runs:200},evmVersion:'cancun',outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}};
const compiled=JSON.parse(solc.compile(json({language:'Solidity',sources:Object.fromEntries(files.map(p=>[p,{content:read(p)}])),settings})));
assert.equal((compiled.errors??[]).filter(e=>e.severity==='error').length,0,json(compiled.errors));
const vn=Object.keys(compiled.contracts['build/Verifier.sol']).find(n=>compiled.contracts['build/Verifier.sol'][n].evm.bytecode.object);
const types={Credential:[{name:'holder',type:'address'},{name:'id',type:'uint256'},{name:'policyVersion',type:'uint256'},{name:'validFrom',type:'uint64'},{name:'validUntil',type:'uint64'},{name:'eligible',type:'bool'}]};
const traces=[],txs=[],proofs=[],summaries=[],stateSamples=[],checks=[],timings=[];
function check(name,extra={}){checks.push({name,passed:true,...extra});}
function expectedEvents(days,shared){let last=null,until=-1;return Array.from({length:100},(_,i)=>{const t=i*9; // tenths of a day, exact integers
  const stale=last!==null&&shared&&days.some(d=>10*d>last&&10*d<=t);
  const event=last===null?'first':(t>=until||stale?'reauthorize':'hit');
  if(event!=='hit'){last=t;until=Math.min(t+300,900);}return event;});}
function errorName(e,interfaces){if(e.revert?.name)return e.revert.name;const d=e.data??e.info?.error?.data;for(const i of interfaces){try{return i.parseError(typeof d==='string'?d:d?.data)?.name;}catch{}}return null;}
async function context({seed=0,mode=1,label}){
  const connection=await network.create({network:'l1',override:{allowBlocksWithSameTimestamp:true}});
  const rpc=connection.provider,provider=new ethers.BrowserProvider(rpc,undefined,{cacheTimeout:-1});provider.pollingInterval=10;
  const signers=await Promise.all(Array.from({length:12},(_,i)=>provider.getSigner(i)));
  const addresses=await Promise.all(signers.map(s=>s.getAddress())),owner=signers[0],holder=signers[5+seed],wallet=addresses[5+seed];
  const base=BigInt((await provider.getBlock('latest')).timestamp)+3600n;
  const fixture=await makeFixtures(addresses.slice(0,4),base);
  // Hold the population fixed across schedules. Twelve distinct other leaves
  // are removed, with matching public IDs, instead of repeatedly revoking one ID.
  for(let j=0;j<12;j++)fixture.credentials[3].push({...fixture.credentials[3][0],secret:900000n+BigInt(j),salt:800000n+BigInt(j)});
  fixture.setCredential(3,0,{});
  if(seed)fixture.setCredential(0,0,{secret:10001n+10000n*BigInt(seed),salt:20001n+10000n*BigInt(seed)});
  async function receipt(tx,kind,extra={}){const r=await tx.wait();assert.equal(r.status,1);const b=await provider.getBlock(r.blockNumber);txs.push({label,kind,...extra,timestamp:b.timestamp,receipt:r.toJSON(),transaction:tx.toJSON()});return r;}
  async function deploy(file,name,args=[]){const a=compiled.contracts[file][name];const c=await new ethers.ContractFactory(a.abi,a.evm.bytecode.object,owner).deploy(...args);await receipt(c.deploymentTransaction(),'setup',{name});await c.waitForDeployment();return c;}
  const hasher=await new ethers.ContractFactory(poseidonContract.generateABI(2),poseidonContract.createCode(2),owner).deploy();await receipt(hasher.deploymentTransaction(),'setup',{name:'Poseidon'});await hasher.waitForDeployment();
  const registry=await deploy('contracts/PolicyRegistry.sol','PolicyRegistry',[addresses[0],hasher.target,addresses.slice(0,4),fixture.policyRoot,fixture.minTier,fixture.maxTTL]);
  const token=await deploy('contracts/MockToken.sol','MockToken',[wallet,ethers.parseUnits('10000000',18)]);
  const verifier=await deploy('build/Verifier.sol',vn);
  for(let i=0;i<4;i++)await receipt(await registry.connect(signers[i]).publishIssuerRoot(i,fixture.issuerRoots[i],false),'setup',{issuer:i});
  assert.equal(await registry.registryRoot(),fixture.registryRoot);
  const gates={},approval={};
  for(const variant of ['signed','zk']){
    const g=await deploy('contracts/PolicyGate.sol','PolicyGate',[registry.target,token.target,verifier.target,variant==='zk',true,mode,0,mode===0?0:300]);gates[variant]=g.connect(holder);
    await receipt(await token.connect(holder).transfer(g.target,1n),'setup',{variant,operation:'bootstrap_balance'});
    approval[variant]=Number((await receipt(await token.connect(holder).approve(g.target,ethers.MaxUint256),'approval',{variant})).gasUsed);
  }
  const credential={holder:wallet,id:101n+BigInt(seed),policyVersion:1n,validFrom:fixture.notBefore,validUntil:fixture.credentialExpiry,eligible:true};
  const domain={name:'PETs4DeFiEligibility',version:'2',chainId:(await provider.getNetwork()).chainId,verifyingContract:registry.target};
  const signature=await signers[0].signTypedData(domain,types,credential);
  const pin=async t=>rpc.request({method:'evm_setNextBlockTimestamp',params:[Number(t)]});
  const advance=async t=>{await pin(t);await rpc.request({method:'evm_mine',params:[]});};
  const state=async g=>({nonce:await g.nonces(wallet),deposit:await g.deposits(wallet),holderBalance:await token.balanceOf(wallet),gateBalance:await token.balanceOf(g.target),cache:Array.from(await g.caches(wallet)),securityEpoch:await registry.securityEpoch()});
  async function proof(g,t){
    const nonce=await g.nonces(wallet),end=t+TTL<fixture.credentialExpiry?t+TTL:fixture.credentialExpiry;
    const scope=await g.computeScope(),requestHash=await g.computeRequestHashForRoot(fixture.registryRoot,wallet,AMOUNT,nonce,t,end);
    const input=fixture.inputFor({scope,requestHash,windowStart:t,windowEnd:end});
    const start=performance.now();const {proof:pr,publicSignals}=await snarkjs.groth16.fullProve(input,'build/access_js/access.wasm','build/access_final.zkey',undefined,undefined,{singleThread:true});
    const ms=performance.now()-start;assert.equal(await snarkjs.groth16.verify(vk,publicSignals,pr),true);
    const tuple=JSON.parse('['+await snarkjs.groth16.exportSolidityCallData(pr,publicSignals)+']');
    proofs.push({label,nonce,t,input,proof:pr,publicSignals,proof_ms:ms});timings.push({label,seed,proof_ms:ms});return {tuple,nonce,ms};
  }
  async function deposit(variant,t,{forceFull=false,expectedEvent=null,index=null}={}){
    await advance(t);const g=gates[variant],before=await state(g);let reason=null,hit=true;
    try{await g.depositCached.staticCall(AMOUNT,before.nonce);}catch(e){reason=errorName(e,[g.interface,registry.interface]);assert(reason);hit=false;}
    if(forceFull)hit=false;
    const event=hit?'hit':before.nonce===0n?'first':'reauthorize';if(expectedEvent)assert.equal(event,expectedEvent,`${label}/${variant}/${index}`);
    const pr=variant==='zk'&&!hit?await proof(g,t):null;await pin(t);
    const tx=hit?await g.depositCached(AMOUNT,before.nonce):variant==='zk'?await g.depositZK(pr.tuple,AMOUNT,before.nonce):await g.depositSigned(credential,signature,AMOUNT,before.nonce);
    const r=await receipt(tx,'deposit',{variant,event,index});const after=await state(g);
    assert.equal(after.nonce,before.nonce+1n);assert.equal(after.deposit,before.deposit+AMOUNT);assert.equal(after.holderBalance,before.holderBalance-AMOUNT);assert.equal(after.gateBalance,before.gateBalance+AMOUNT);
    assert.equal(BigInt((await provider.getBlock(r.blockNumber)).timestamp),t);
    if(!hit)assert.equal(after.cache[0],t+TTL<fixture.credentialExpiry?t+TTL:fixture.credentialExpiry);
    const row={label,variant,index,day_seconds:t-base,event,reason,gas:Number(r.gasUsed),tx_hash:r.hash,proof_ms:pr?.ms??null,before,after};traces.push(row);return {row,pr};
  }
  async function otherRevocation(j,t){await advance(t);const issuer=3,index=j+2,id=300n+BigInt(index);const newRoot=fixture.removeCredential(issuer,index);await pin(t);await receipt(await registry.connect(signers[issuer]).revokeAndPublish(issuer,id,newRoot),'revocation',{issuer,leaf_index:index,public_id:id});assert.equal(await registry.registryRoot(),fixture.registryRoot);}
  async function reject(name,variant,method,args,t,expected){await advance(t);const g=gates[variant],before=await state(g);let reason=null;
    try{await g[method].staticCall(...args);}catch(e){reason=errorName(e,[g.interface,registry.interface]);}assert.equal(reason,expected,name);
    await pin(t);const tx=await g[method](...args,{gasLimit:1200000});let r;try{r=await tx.wait();}catch(e){r=e.receipt;}assert(r);assert.equal(r.status,0,name);assert.deepEqual(await state(g),before,name);
    txs.push({label,kind:'rejected',name,variant,timestamp:Number(t),receipt:r.toJSON(),transaction:tx.toJSON()});check(name,{reason,tx_hash:r.hash});
  }
  return {connection,rpc,provider,registry,token,signers,fixture,base,wallet,gates,credential,signature,approval,deposit,proof,state,advance,pin,receipt,otherRevocation,reject};
}

const schedules=[{name:'aligned_30_60',days:[30,60],k:3},{name:'phase_15_45',days:[15,45],k:4},{name:'restart_31_63',days:[31,63],k:5},{name:'weekly',days:Array.from({length:12},(_,i)=>7*(i+1)),k:13}];
try{
  for(const s of schedules){const c=await context({label:s.name});let next=0;const expected={signed:expectedEvents(s.days,false),zk:expectedEvents(s.days,true)};
    for(let i=0;i<100;i++){const t=c.base+BigInt(i)*9n*DAY/10n;
      while(next<s.days.length&&BigInt(s.days[next])*DAY<=t-c.base){await c.otherRevocation(next,c.base+BigInt(s.days[next])*DAY);next++;}
      for(const v of ['signed','zk'])await c.deposit(v,t,{index:i,expectedEvent:expected[v][i]});
    }
    for(const v of ['signed','zk']){const rows=traces.filter(r=>r.label===s.name&&r.variant===v);const k=rows.filter(r=>r.event!=='hit').length;assert.equal(k,v==='zk'?s.k:3);summaries.push({schedule:s.name,variant:v,revocations:s.days,authorizations:k,hits:100-k,approval_gas:c.approval[v],gas:c.approval[v]+rows.reduce((a,r)=>a+r.gas,0)});}
    check(`E1 ${s.name}: all 200 paths, timestamps, state transitions and counts match`);console.log(`PASS E1 ${s.name}`);await c.connection.close();
  }
  // Causal diagnostic: an existing signed global-publication mode deliberately
  // adopts shared invalidation. Only revocations occur in these two traces.
  for(const s of [schedules[0],schedules[3]]){const label=`shared_signed_${s.name}`,c=await context({label,mode:0});let next=0;const expected=expectedEvents(s.days,true);
    for(let i=0;i<100;i++){const t=c.base+BigInt(i)*9n*DAY/10n;while(next<s.days.length&&BigInt(s.days[next])*DAY<=t-c.base){await c.otherRevocation(next,c.base+BigInt(s.days[next])*DAY);next++;}await c.deposit('signed',t,{index:i,expectedEvent:expected[i]});}
    const rows=traces.filter(r=>r.label===label);assert.equal(rows.filter(r=>r.event!=='hit').length,s.k);summaries.push({schedule:label,variant:'signed_global',revocations:s.days,authorizations:s.k,hits:100-s.k,approval_gas:c.approval.signed,gas:c.approval.signed+rows.reduce((a,r)=>a+r.gas,0)});check(`diagnostic ${label}`);console.log(`PASS diagnostic ${label}`);await c.connection.close();
  }
  for(let seed=1;seed<=5;seed++){const label=`holder_${seed}`,c=await context({seed,label}),sample={signed:{seed,variant:'signed',approval:c.approval.signed},zk:{seed,variant:'zk',approval:c.approval.zk}};
    for(const [event,offset] of [['first',0n],['hit',DAY],['reauthorize',TTL]])for(const v of ['signed','zk'])sample[v][event]=(await c.deposit(v,c.base+offset,{expectedEvent:event})).row.gas;
    stateSamples.push(sample.signed,sample.zk);
    check(`E2 distinct holder/credential seed ${seed}`);console.log(`PASS E2 holder ${seed}`);await c.connection.close();
  }
  {
    const c=await context({label:'negative_controls'});await c.deposit('signed',c.base);const used=await c.deposit('zk',c.base);
    await c.reject('used proof nonce replay','zk','depositZK',[used.pr.tuple,AMOUNT,used.pr.nonce],c.base+1n,'InvalidNonce');
    for(const v of ['signed','zk'])await c.reject(`${v} expired cache at exact TTL`,v,'depositCached',[AMOUNT,await c.gates[v].nonces(c.wallet)],c.base+TTL,'AuthorizationExpired');
    for(const v of ['signed','zk'])await c.deposit(v,c.base+TTL,{expectedEvent:'reauthorize'});
    const t=c.base+TTL+DAY,stale=await c.proof(c.gates.zk,t);await c.advance(t);const newRoot=c.fixture.removeCredential(0,0);await c.pin(t);await c.receipt(await c.registry.connect(c.signers[0]).revokeAndPublish(0,c.credential.id,newRoot),'own_revocation');
    await c.reject('signed own revocation cached','signed','depositCached',[AMOUNT,await c.gates.signed.nonces(c.wallet)],t,'CredentialRevoked');
    await c.reject('ZK own revocation cached','zk','depositCached',[AMOUNT,await c.gates.zk.nonces(c.wallet)],t,'StaleAuthorization');
    await c.reject('signed revoked full authorization','signed','depositSigned',[c.credential,c.signature,AMOUNT,await c.gates.signed.nonces(c.wallet)],t,'CredentialRevoked');
    await c.reject('pre-update ZK proof after authoritative revocation','zk','depositZK',[stale.tuple,AMOUNT,stale.nonce],t,'InvalidPublicSignals');
    await c.connection.close();console.log('PASS exact TTL, replay and paired own revocation controls');
  }
  const sourceFiles=['package.json','package-lock.json','hardhat.config.js','circuits/access.circom',...files.filter(x=>!x.startsWith('build/')),'scripts/fixtures.mjs','scripts/revocation_validation.mjs'];
  const report={schema_version:1,status:'PASS',created_utc:new Date().toISOString(),metadata:{base_commit:'d4031faa59ba5dd1781b663b676dc2c443bdc64f',git_head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),node:process.version,cpu:os.cpus()[0]?.model,logical_cpus:os.cpus().length,solc:solc.version(),settings,hardfork:'osaka',timestamp_override:'allowBlocksWithSameTimestamp=true: ordered updates before access at exact modeled times',fixture:'20 synthetic credentials: original 8 plus 12 other leaves in issuer 3; identical population in every trace; five E2 seeds vary holder, secret, salt and public ID',source_files_sha256:Object.fromEntries(sourceFiles.map(p=>[p,hash(fs.readFileSync(p))])),setup},summaries,stateSamples,checks,proof_timing_diagnostic:timings,counts:{core_accesses:800,shared_signed_control_accesses:200,state_sample_accesses:30,negative_control_failures:7,proofs:proofs.length},limits:'Local execution only; E2 five fresh holders are a state diagnostic, not a statistical population. Proof durations here are diagnostic sequential server samples, not physical-device UX. Setup phase 2 is one-process demonstration only.'};
  fs.writeFileSync(path.join(out,'validation_report.json'),json(report));fs.writeFileSync(path.join(out,'traces.json'),json(traces));
  fs.writeFileSync(path.join(out,'receipts_and_proofs.json.gz'),gzipSync(json({transactions:txs,proofs}),{level:9}));
  fs.writeFileSync(path.join(out,'verification_key.json'),json(vk));fs.copyFileSync('build/Verifier.sol',path.join(out,'Verifier.sol'));
  fs.writeFileSync(path.join(out,'manifest.json'),json(Object.fromEntries(fs.readdirSync(out).filter(n=>n!=='manifest.json').map(n=>[n,hash(fs.readFileSync(path.join(out,n)))]))));
  console.log(json({status:'PASS',summaries,checks:checks.length,proofs:proofs.length}));
}catch(e){fs.writeFileSync(path.join(out,'FAILED.json'),json({error:e.message,stack:e.stack,completed_summaries:summaries,completed_checks:checks}));throw e;}
process.exit(0);
