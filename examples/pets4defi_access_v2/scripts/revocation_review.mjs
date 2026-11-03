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
const out=path.resolve(process.env.VALIDATION_OUT??'results/revocation_review');fs.mkdirSync(out,{recursive:true});
const DAY=86400n,TTL=30n*DAY,AMOUNT=ethers.parseUnits('100',18);
const json=x=>JSON.stringify(x,(_,v)=>typeof v==='bigint'?v.toString():v,2)+'\n';
const hash=x=>createHash('sha256').update(x).digest('hex');
const read=p=>fs.readFileSync(p,'utf8');
function gitHead(){try{return execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8',stdio:['ignore','pipe','ignore']}).trim();}catch{return null;}}
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
async function context({seed=0,mode=1,label,groupCount=1}){
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
  assert([1,2,4].includes(groupCount));
  const groupFixtures=[fixture];
  for(let g=1;g<groupCount;g++){
    const f=await makeFixtures(addresses.slice(0,4),base);
    for(let j=0;j<12;j++)f.credentials[3].push({...f.credentials[3][0],secret:900000n+BigInt(j),salt:800000n+BigInt(j)});
    f.setCredential(3,0,{});groupFixtures.push(f);
  }
  for(let g=0;g<groupCount;g++)for(let i=0;i<4;i++)if(Math.floor(i/(4/groupCount))!==g)groupFixtures[g].setIssuerDisabled(i);
  async function receipt(tx,kind,extra={}){const r=await tx.wait();assert.equal(r.status,1);const b=await provider.getBlock(r.blockNumber);txs.push({label,kind,...extra,timestamp:b.timestamp,receipt:r.toJSON(),transaction:tx.toJSON()});return r;}
  async function deploy(file,name,args=[]){const a=compiled.contracts[file][name];const c=await new ethers.ContractFactory(a.abi,a.evm.bytecode.object,owner).deploy(...args);await receipt(c.deploymentTransaction(),'setup',{name});await c.waitForDeployment();return c;}
  const hasher=await new ethers.ContractFactory(poseidonContract.generateABI(2),poseidonContract.createCode(2),owner).deploy();await receipt(hasher.deploymentTransaction(),'setup',{name:'Poseidon'});await hasher.waitForDeployment();
  const groupRegistries=[];
  for(let g=0;g<groupCount;g++)groupRegistries.push(await deploy('contracts/PolicyRegistry.sol','PolicyRegistry',[addresses[0],hasher.target,addresses.slice(0,4),fixture.policyRoot,fixture.minTier,fixture.maxTTL]));
  const registry=groupRegistries[0];
  // Enforce disjoint groups on chain. An unpublished zero root alone would
  // still let an excluded issuer activate itself later in this registry.
  for(let g=0;g<groupCount;g++)for(let i=0;i<4;i++)if(Math.floor(i/(4/groupCount))!==g){
    await receipt(await groupRegistries[g].disableIssuer(i),'setup',{operation:'permanently_exclude_issuer',group:g,issuer:i});
    await assert.rejects(groupRegistries[g].connect(signers[i]).publishIssuerRoot.staticCall(i,groupFixtures[g].issuerRoots[i],false),e=>errorName(e,[groupRegistries[g].interface])==='InactiveIssuer');
    check(`partition B=${groupCount} group ${g}: excluded issuer ${i} cannot publish`);
  }
  const token=await deploy('contracts/MockToken.sol','MockToken',[wallet,ethers.parseUnits('10000000',18)]);
  const verifier=await deploy('build/Verifier.sol',vn);
  for(let i=0;i<4;i++){const group=Math.floor(i/(4/groupCount));await receipt(await groupRegistries[group].connect(signers[i]).publishIssuerRoot(i,groupFixtures[group].issuerRoots[i],false),'setup',{issuer:i,group});}
  for(let g=0;g<groupCount;g++)assert.equal(await groupRegistries[g].registryRoot(),groupFixtures[g].registryRoot);
  const gates={},approval={};
  for(const variant of ['signed','zk']){
    const g=await deploy('contracts/PolicyGate.sol','PolicyGate',[registry.target,token.target,verifier.target,variant==='zk',true,mode,0,mode===0?0:300]);gates[variant]=g.connect(holder);
    await receipt(await token.connect(holder).transfer(g.target,1n),'setup',{variant,operation:'bootstrap_balance'});
    approval[variant]=Number((await receipt(await token.connect(holder).approve(g.target,ethers.MaxUint256),'approval',{variant})).gasUsed);
  }
  const groupGates=[gates.zk];
  for(let g=1;g<groupCount;g++)groupGates.push((await deploy('contracts/PolicyGate.sol','PolicyGate',[groupRegistries[g].target,token.target,verifier.target,true,true,1,0,300])).connect(holder));
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
  async function otherRevocation(j,t,issuer=3,index=j+2){
    const group=Math.floor(issuer/(4/groupCount)), reg=groupRegistries[group],f=groupFixtures[group];
    const oldEpochs=await Promise.all(groupRegistries.map(r=>r.securityEpoch()));
    await advance(t);const id=300n+BigInt(issuer*100+index),newRoot=f.removeCredential(issuer,index);await pin(t);
    await receipt(await reg.connect(signers[issuer]).revokeAndPublish(issuer,id,newRoot),'revocation',{issuer,group,leaf_index:index,public_id:id});
    for(let g=0;g<groupCount;g++){
      assert.equal(await groupRegistries[g].registryRoot(),groupFixtures[g].registryRoot);
      assert.equal(await groupRegistries[g].securityEpoch(),oldEpochs[g]+(g===group?1n:0n));
    }
  }
  async function reject(name,variant,method,args,t,expected){await advance(t);const g=gates[variant],before=await state(g);let reason=null;
    try{await g[method].staticCall(...args);}catch(e){reason=errorName(e,[g.interface,registry.interface]);}assert.equal(reason,expected,name);
    await pin(t);const tx=await g[method](...args,{gasLimit:1200000});let r;try{r=await tx.wait();}catch(e){r=e.receipt;}assert(r);assert.equal(r.status,0,name);assert.deepEqual(await state(g),before,name);
    txs.push({label,kind:'rejected',name,variant,timestamp:Number(t),receipt:r.toJSON(),transaction:tx.toJSON()});check(name,{reason,tx_hash:r.hash});
  }
  return {connection,rpc,provider,registry,token,signers,fixture,base,wallet,gates,credential,signature,approval,deposit,proof,state,advance,pin,receipt,otherRevocation,reject,groupRegistries,groupGates};
}

const schedules=[{name:'aligned_30_60',days:[30,60],k:3},{name:'phase_15_45',days:[15,45],k:4},{name:'restart_31_63',days:[31,63],k:5},{name:'weekly',days:Array.from({length:12},(_,i)=>7*(i+1)),k:13}];
const repeats=Number(process.env.VALIDATION_REPEATS??3);
assert(Number.isInteger(repeats)&&repeats>=1&&repeats<=10);
function addSummary(c,s,label,variant,extra={}){
  const v=variant==='signed_global'?'signed':variant;
  const rows=traces.filter(r=>r.label===label&&r.variant===v),k=rows.filter(r=>r.event!=='hit').length;
  assert.equal(rows.length,100);assert.equal(k,v==='signed'&&variant!=='signed_global'?3:s.k);
  summaries.push({schedule:label,base_schedule:s.name,variant,revocations:s.days,authorizations:k,hits:100-k,approval_gas:c.approval[v],gas:c.approval[v]+rows.reduce((a,r)=>a+r.gas,0),...extra});
}
function save(status,error=null){
  const sourceFiles=['package.json','package-lock.json','hardhat.config.js','circuits/access.circom',...files.filter(x=>!x.startsWith('build/')),'scripts/fixtures.mjs','scripts/revocation_review.mjs','scripts/setup.mjs'];
  const report={schema_version:2,status,created_utc:new Date().toISOString(),metadata:{base_commit:'dde8b677c4f1fb01673041ece76fe3b87fce97dc',git_head:gitHead(),node:process.version,cpu:os.cpus()[0]?.model,logical_cpus:os.cpus().length,solc:solc.version(),settings,hardfork:'osaka',repetitions:repeats,timestamp_override:'updates before access at exact modeled times',fixture:'Same 20 synthetic credentials. Group partition uses 1, 2 or 4 registries, disjoint public issuer groups, unchanged circuit width and contracts.',source_files_sha256:Object.fromEntries(sourceFiles.map(p=>[p,hash(fs.readFileSync(p))])),setup},summaries,stateSamples,checks,proof_timing_diagnostic:timings,counts:{core_accesses:800*repeats,shared_signed_control_accesses:400,group_accesses:300,negative_control_failures:txs.filter(r=>r.kind==='rejected').length,proofs:proofs.length},limits:'Three full replays vary proof randomness under one local setup. They are not independent workloads or devices. Partitions reveal issuer group. Setup and issuer-update gas are retained separately; no total system optimization claimed.',error};
  fs.writeFileSync(path.join(out,'validation_report.json'),json(report));fs.writeFileSync(path.join(out,'traces.json'),json(traces));
  fs.writeFileSync(path.join(out,'receipts_and_proofs.json.gz'),gzipSync(json({transactions:txs,proofs}),{level:9}));
  fs.writeFileSync(path.join(out,'verification_key.json'),json(vk));fs.copyFileSync('build/Verifier.sol',path.join(out,'Verifier.sol'));
  const names=['validation_report.json','traces.json','receipts_and_proofs.json.gz','verification_key.json','Verifier.sol'];
  fs.writeFileSync(path.join(out,'manifest.json'),json(Object.fromEntries(names.map(n=>[n,hash(fs.readFileSync(path.join(out,n)))]))));
}
try{
  for(let repetition=1;repetition<=repeats;repetition++)for(const s of schedules){
    const label=`repeat_${repetition}_${s.name}`,c=await context({label});let next=0;
    const expected={signed:expectedEvents(s.days,false),zk:expectedEvents(s.days,true)};
    for(let i=0;i<100;i++){const t=c.base+BigInt(i)*9n*DAY/10n;
      while(next<s.days.length&&BigInt(s.days[next])*DAY<=t-c.base){await c.otherRevocation(next,c.base+BigInt(s.days[next])*DAY);next++;}
      for(const v of ['signed','zk'])await c.deposit(v,t,{index:i,expectedEvent:expected[v][i]});
    }
    for(const v of ['signed','zk'])addSummary(c,s,label,v,{repetition});
    check(`complete paired replay ${label}`);console.log(`PASS ${label}`);await c.connection.close();save('RUNNING');
  }
  for(const s of schedules){
    const label=`shared_signed_${s.name}`,c=await context({label,mode:0});let next=0;const expected=expectedEvents(s.days,true);
    for(let i=0;i<100;i++){const t=c.base+BigInt(i)*9n*DAY/10n;
      while(next<s.days.length&&BigInt(s.days[next])*DAY<=t-c.base){await c.otherRevocation(next,c.base+BigInt(s.days[next])*DAY);next++;}
      await c.deposit('signed',t,{index:i,expectedEvent:expected[i]});
    }
    addSummary(c,s,label,'signed_global');check(`signed count control ${label}`);console.log(`PASS ${label}`);await c.connection.close();save('RUNNING');
  }
  // Same two publications and issuer assignments in all partition cases.
  // Public groups are contiguous: B=2 -> {0,1}/{2,3}; B=4 -> singleton issuers.
  for(const B of [1,2,4]){
    const label=`partition_B${B}`,c=await context({label,groupCount:B});
    const events=[{day:31,issuer:3,index:2},{day:63,issuer:1,index:1}];
    const relevant=events.filter(e=>Math.floor(e.issuer/(4/B))===0).map(e=>e.day);
    const expected=expectedEvents(relevant,true);let next=0;
    for(let i=0;i<100;i++){const t=c.base+BigInt(i)*9n*DAY/10n;
      while(next<events.length&&BigInt(events[next].day)*DAY<=t-c.base){const e=events[next];await c.otherRevocation(next,c.base+BigInt(e.day)*DAY,e.issuer,e.index);next++;}
      await c.deposit('zk',t,{index:i,expectedEvent:expected[i]});
    }
    const k=expected.filter(x=>x!=='hit').length;
    addSummary(c,{name:'partition_31_63',days:relevant,k},label,'zk',{groups:B,published_revocations:events,issuer_options:4/B,setup_gas:txs.filter(r=>r.label===label&&r.kind==='setup').reduce((a,r)=>a+Number(r.receipt.gasUsed),0),publication_gas:txs.filter(r=>r.label===label&&r.kind==='revocation').reduce((a,r)=>a+Number(r.receipt.gasUsed),0)});
    check(`partition B=${B}: only the publishing group advanced`);
    const t=c.base+89n*DAY+DAY/5n,stale=await c.proof(c.gates.zk,t);
    if(B>1){
      const other=c.groupGates[1];let reason=null;
      try{await other.depositZK.staticCall(stale.tuple,AMOUNT,0);}catch(e){reason=errorName(e,[other.interface,c.registry.interface]);}
      assert.equal(reason,'InvalidPublicSignals');check(`partition B=${B}: proof cannot migrate to another group gate`,{reason});
    }
    await c.advance(t);const newRoot=c.fixture.removeCredential(0,0);await c.pin(t);
    await c.receipt(await c.registry.connect(c.signers[0]).revokeAndPublish(0,c.credential.id,newRoot),'own_revocation');
    await c.reject(`B=${B} own-revoked cached authorization`,'zk','depositCached',[AMOUNT,await c.gates.zk.nonces(c.wallet)],t,'StaleAuthorization');
    await c.reject(`B=${B} proof from before own revocation`,'zk','depositZK',[stale.tuple,AMOUNT,stale.nonce],t,'InvalidPublicSignals');
    console.log(`PASS ${label} k=${k}, own-revocation and group-boundary checks`);await c.connection.close();save('RUNNING');
  }
  save('PASS');console.log(json({status:'PASS',summaries,checks:checks.length,proofs:proofs.length}));
}catch(e){save('FAIL',{message:e.message,stack:e.stack});throw e;}
process.exit(0);
