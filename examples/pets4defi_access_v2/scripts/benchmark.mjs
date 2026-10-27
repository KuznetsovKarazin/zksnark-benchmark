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

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
process.chdir(root);
const RUNS = Number(process.env.BENCH_RUNS ?? 30);
assert(Number.isInteger(RUNS) && RUNS >= 1 && RUNS <= 1000, 'BENCH_RUNS must be an integer from 1 to 1000');
const CHAINS = (process.env.BENCH_CHAINS ?? 'l1,op').split(',');
assert(CHAINS.length && CHAINS.every(c => ['l1','op'].includes(c)) && new Set(CHAINS).size === CHAINS.length);
const FIELD = 21888242871839275222246405745257275088548364400416034343698204186575808495617n;
const MASK = (1n << 248n) - 1n;
const AMOUNT = ethers.parseUnits('100', 18);
const VARIANTS = ['signed_direct','signed_cache','zk_direct','zk_cache'];
const events = [], tests = [], transactions = [], proofSamples = [], environments = [];
const read = p => fs.readFileSync(p, 'utf8');
const sha = value => createHash('sha256').update(value).digest('hex');
const json = value => JSON.stringify(value, (_, v) => typeof v === 'bigint' ? v.toString() : v, 2) + '\n';
const write = (p, value) => fs.writeFileSync(p, json(value));
fs.mkdirSync('results/proofs', {recursive:true});

const setup = JSON.parse(read('build/setup.json'));
for (const [key,p] of Object.entries({circuit_sha256:'circuits/access.circom',lock_sha256:'package-lock.json',
  zkey_sha256:'build/access_final.zkey',wasm_sha256:'build/access_js/access.wasm',
  verifier_sha256:'build/Verifier.sol',verification_key_sha256:'build/verification_key.json'})) {
  assert.equal(setup[key], sha(fs.readFileSync(p)), `Stale setup artifact ${p}; run npm run setup`);
}
const vkey = JSON.parse(read('build/verification_key.json'));
const files = ['contracts/AccessRegistry.sol','contracts/AccessGate.sol','contracts/MockToken.sol','contracts/AdversarialToken.sol','build/Verifier.sol'];
const sources = Object.fromEntries(files.map(p => [p,{content:read(p)}]));
const compilerSettings = {optimizer:{enabled:true,runs:200},evmVersion:'cancun',
  outputSelection:{'*':{'*':['abi','evm.bytecode.object','evm.deployedBytecode.object']}}};
const compiled = JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources,settings:compilerSettings})));
const compileErrors = (compiled.errors ?? []).filter(e => e.severity === 'error');
assert.equal(compileErrors.length,0,compileErrors.map(e=>e.formattedMessage).join('\n'));
const artifact = (file,name) => compiled.contracts[file][name];
const verifierName = Object.keys(compiled.contracts['build/Verifier.sol']).find(n=>compiled.contracts['build/Verifier.sol'][n].evm.bytecode.object);
const types = {Credential:[{name:'holder',type:'address'},{name:'id',type:'uint256'},
  {name:'policyVersion',type:'uint256'},{name:'validFrom',type:'uint64'},{name:'validUntil',type:'uint64'},{name:'eligible',type:'bool'}]};
const isZK = variant => variant.startsWith('zk');
const cached = variant => variant.endsWith('_cache');

async function fullProof(input, label, chain, costSample=false) {
  const started = performance.now();
  const {proof,publicSignals} = await snarkjs.groth16.fullProve(input,
    'build/access_js/access.wasm','build/access_final.zkey',undefined,undefined,{singleThread:true});
  const proofMs = performance.now()-started;
  const verifyStart = performance.now();
  assert.equal(await snarkjs.groth16.verify(vkey,publicSignals,proof),true,'strict off-chain proof verification');
  const verifyMs = performance.now()-verifyStart;
  const tuple = JSON.parse('['+await snarkjs.groth16.exportSolidityCallData(proof,publicSignals)+']');
  assert.equal(tuple[3].length,8);
  const result = {input,proof,publicSignals,tuple,proof_time_ms:proofMs,offchain_verify_ms:verifyMs};
  proofSamples.push({chain,label,cost_sample:costSample,proof_time_ms:proofMs,
    offchain_verify_ms:verifyMs,public_signals:publicSignals,proof_sha256:sha(json(proof))});
  return result;
}

async function runChain(chain) {
  const connection = await network.create(chain);
  const rpc = connection.provider;
  const provider = new ethers.BrowserProvider(rpc,undefined,{cacheTimeout:-1});
  provider.pollingInterval=10;
  try {
    const signers = await Promise.all(Array.from({length:8},(_,i)=>provider.getSigner(i)));
    const addresses = await Promise.all(signers.map(s=>s.getAddress()));
    const [owner] = signers;
    const holder=signers[5], fresh=signers[6], attacker=signers[7];
    const holderAddress=addresses[5], freshAddress=addresses[6];
    const chainId=(await provider.getNetwork()).chainId;
    const now=async()=>BigInt((await provider.getBlock('latest')).timestamp);
    const fixtureTime=await now();
    const fixtures=await makeFixtures(addresses.slice(0,4),fixtureTime);
    const check=(name,details={})=>tests.push({chain,name,passed:true,...details});
    async function record(tx,variant,event,run=0,extra={},measured=true) {
      const receipt=await tx.wait();
      assert.equal(receipt.status,1,`${chain}/${event}: transaction failed`);
      transactions.push({chain,variant,event,run,receipt:receipt.toJSON()});
      if(measured) events.push({chain,variant,event,run,gas_used:Number(receipt.gasUsed),
        proof_time_ms:null,offchain_verify_ms:null,tx_hash:receipt.hash,
        scope:event.startsWith('deploy_')||event==='bootstrap_token_balance'||event==='issuer_root_initial'?'shared_fixed':
          event==='issuer_root_update'?'per_registry_update':'per_action',
        evidence_status:'measured_local',...extra});
      return receipt;
    }
    async function deploy(file,name,args,variant,event,measured=true) {
      const a=artifact(file,name);
      const contract=await new ethers.ContractFactory(a.abi,a.evm.bytecode.object,owner).deploy(...args);
      await record(contract.deploymentTransaction(),variant,event,0,{},measured);
      await contract.waitForDeployment();
      return contract;
    }
    const hasher=await new ethers.ContractFactory(poseidonContract.generateABI(2),poseidonContract.createCode(2),owner).deploy();
    await record(hasher.deploymentTransaction(),'shared','deploy_poseidon');
    await hasher.waitForDeployment();
    assert.equal(await hasher['poseidon(uint256[2])']([21n,BigInt(addresses[0])]),fixtures.hash(21n,BigInt(addresses[0])));
    const registry=await deploy('contracts/AccessRegistry.sol','AccessRegistry',
      [addresses[0],await hasher.getAddress(),addresses.slice(0,4),fixtures.policyRoot,fixtures.minTier,fixtures.maxTTL],
      'shared','deploy_registry');
    const token=await deploy('contracts/MockToken.sol','MockToken',
      [holderAddress,ethers.parseUnits('10000000',18)],'shared','deploy_token');
    const verifier=await deploy('build/Verifier.sol',verifierName,[],'shared','deploy_verifier');
    for(let i=0;i<4;i++) await record(await registry.connect(signers[i]).setIssuerRoot(i,fixtures.issuerRoots[i]),
      'shared','issuer_root_initial',i,{issuer_index:i});
    assert.equal(await registry.registryRoot(),fixtures.registryRoot);
    check('authenticated issuer hierarchy matches independent Poseidon fixture');
    const gates={};
    for(const variant of VARIANTS) {
      gates[variant]=(await deploy('contracts/AccessGate.sol','AccessGate',
        [await registry.getAddress(),await token.getAddress(),await verifier.getAddress(),isZK(variant),cached(variant)],
        variant,'deploy_gate')).connect(holder);
      await record(await token.connect(holder).transfer(await gates[variant].getAddress(),1n),variant,'bootstrap_token_balance');
      await record(await token.connect(holder).approve(await gates[variant].getAddress(),ethers.MaxUint256),variant,'approve');
    }
    const domain={name:'PETs4DeFiEligibility',version:'2',chainId,verifyingContract:await registry.getAddress()};
    const credential={holder:holderAddress,id:101n,policyVersion:await registry.policyVersion(),validFrom:fixtures.notBefore,validUntil:fixtures.credentialExpiry,eligible:true};
    const sign=(c=credential,signer=signers[0],overrides={})=>signer.signTypedData({...domain,...overrides},types,c);
    const signature=await sign();
    for(const variant of ['signed_direct','signed_cache']) {
      assert.equal(await gates[variant].hashCredential(credential),ethers.TypedDataEncoder.hash(domain,types,credential));
      check(`${variant}: registry-domain credential digest matches independent encoding`);
    }
    async function proofFor(gate,amount=AMOUNT,nonce,options={}) {
      const wallet=options.wallet??holderAddress;
      nonce ??= await gate.nonces(wallet);
      const start=options.windowStart??await now();
      const end=options.windowEnd??start+fixtures.maxTTL;
      const epoch=await registry.epoch();
      const tokenAddress=await gate.token();
      const scope=BigInt(ethers.keccak256(ethers.AbiCoder.defaultAbiCoder().encode(
        ['uint256','address','uint256'],[chainId,await gate.getAddress(),1n])))%FIELD;
      assert.equal(scope,await gate.computeScope());
      const request=BigInt(ethers.keccak256(ethers.AbiCoder.defaultAbiCoder().encode(
        ['uint256','address','address','address','uint256','uint256','uint256','uint64','uint64'],
        [chainId,await gate.getAddress(),wallet,tokenAddress,amount,nonce,epoch,start,end])))&MASK;
      assert.equal(request,await gate.computeRequestHash(wallet,amount,nonce,start,end));
      const input=fixtures.inputFor({scope,requestHash:request,windowStart:start,windowEnd:end,
        issuerIndex:options.issuerIndex??0,credentialIndex:options.credentialIndex??0,...options.overrides});
      if(chain==='l1'&&!fs.existsSync('build/browser_input.json')) write('build/browser_input.json',input);
      const p=await fullProof(input,options.label??'diagnostic',chain,options.costSample??false);
      assert.equal(BigInt(p.publicSignals[1]),fixtures.registryRoot);
      assert.equal(BigInt(p.publicSignals[7]),request);
      return p;
    }
    async function state(gate,wallet=holderAddress,asset=token) {
      const gateAddress=await gate.getAddress();
      return {nonce:await gate.nonces(wallet),deposit:await gate.deposits(wallet),
        holderBalance:await asset.balanceOf(wallet),gateBalance:await asset.balanceOf(gateAddress),
        cache:Array.from(await gate.caches(wallet))};
    }
    async function successful(variant,event,run,options={}) {
      const gate=gates[variant],before=await state(gate);
      const useCache=event==='cache_hit';
      const p=isZK(variant)&&!useCache?await proofFor(gate,AMOUNT,before.nonce,{label:`${variant}/${event}/${run}`,costSample:options.measured!==false}):null;
      const tx=useCache?await gate.depositCached(AMOUNT,before.nonce):isZK(variant)?
        await gate.depositZK(p.tuple,AMOUNT,before.nonce):await gate.depositSigned(credential,signature,AMOUNT,before.nonce);
      const receipt=await record(tx,variant,event,run,{proof_time_ms:p?.proof_time_ms??null,
        offchain_verify_ms:p?.offchain_verify_ms??null},options.measured!==false);
      const after=await state(gate);
      assert.equal(after.nonce,before.nonce+1n);assert.equal(after.deposit,before.deposit+AMOUNT);
      assert.equal(after.holderBalance,before.holderBalance-AMOUNT);assert.equal(after.gateBalance,before.gateBalance+AMOUNT);
      if(cached(variant)) {assert.equal(after.cache[1],await registry.epoch());assert(after.cache[0]>await now());}
      check(`${variant}: ${event} ${run} transfers token and consumes nonce`,{tx_hash:receipt.hash});
      if(run===0&&p&&['access_first','cache_register_first'].includes(event)) {
        write(`results/proofs/${chain}-${variant}-first.json`,p);
      }
      return p;
    }
    for(const variant of VARIANTS) {
      await successful(variant,cached(variant)?'cache_register_first':'access_first',0);
      for(let run=1;run<=RUNS;run++) await successful(variant,cached(variant)?'cache_hit':'access_repeat',run);
      console.log(`${chain} ${variant}: first + ${RUNS} warm actions passed`);
    }

    async function staticReject(label,contract,method,args,expected,signer=holder,extraInterfaces=[]) {
      let rejected=false;
      try {await contract.connect(signer)[method].staticCall(...args);}
      catch(error) {
        if(error.code!=='CALL_EXCEPTION') throw error;
        let reason=error.revert?.name;
        if(!reason&&error.data) for(const iface of [contract.interface,...extraInterfaces]) {
          try {reason=iface.parseError(error.data)?.name;if(reason)break;}catch{}
        }
        assert.equal(reason,expected,`${chain}/${label}: unexpected error`);rejected=true;
      }
      assert(rejected,`${chain}/${label}: unexpectedly accepted`);
      check(label,{expected_error:expected,phase:'static_call'});
    }
    async function reject(label,gate,method,args,expected,{signer=holder,asset=token,variant='diagnostic'}={}) {
      const before=await state(gate,holderAddress,asset);
      const senderAddress=await signer.getAddress();
      const senderBefore=await state(gate,senderAddress,asset);
      const nullifiers=method==='depositZK'?[BigInt(args[0][3][0])]:[];
      const beforeBindings=await Promise.all(nullifiers.map(n=>gate.nullifierHolder(n)));
      await staticReject(label,gate,method,args,expected,signer,[asset.interface]);
      let receipt;
      try {const tx=await gate.connect(signer)[method](...args,{gasLimit:2000000n});await tx.wait();}
      catch(error) {if(error.code!=='CALL_EXCEPTION'||!error.receipt)throw error;receipt=error.receipt;}
      assert(receipt&&receipt.status===0,`${label}: reverted transaction missing`);
      assert.deepEqual(await state(gate,holderAddress,asset),before,`${label}: changed state`);
      assert.deepEqual(await state(gate,senderAddress,asset),senderBefore,`${label}: changed sender state`);
      assert.deepEqual(await Promise.all(nullifiers.map(n=>gate.nullifierHolder(n))),beforeBindings);
      transactions.push({chain,variant,event:'negative',name:label,receipt:receipt.toJSON()});
      check(`${label}: included revert preserves state`,{expected_error:expected,gas_used:Number(receipt.gasUsed),tx_hash:receipt.hash,state_unchanged:true});
    }

    // Change a non-target credential, preserving the target holder's validity.
    // Global invalidation is deliberate: all caches must be refreshed.
    for(let run=1;run<=RUNS;run++) {
      const t=performance.now();const nextRoot=fixtures.refreshRoot(3,run);const updateMs=performance.now()-t;
      await record(await registry.connect(signers[3]).setIssuerRoot(3,nextRoot),'shared','issuer_root_update',run,{issuer_index:3,issuer_tree_update_ms:updateMs});
      assert.equal(await registry.registryRoot(),fixtures.registryRoot);
      for(const variant of ['signed_cache','zk_cache']) {
        await staticReject(`${variant}: epoch change invalidates cache ${run}`,gates[variant],'depositCached',
          [AMOUNT,await gates[variant].nonces(holderAddress)],'StaleAuthorization');
        await successful(variant,'cache_reauthorize',run);
      }
    }
    console.log(`${chain}: ${RUNS} root updates and cache refresh pairs passed`);

    // Registry authorization: no arbitrary third party or owner can overwrite
    // another issuer's credential tree, including the fixed-owner account.
    await staticReject('untrusted account cannot update issuer root',registry,'setIssuerRoot',[0,123n],'NotIssuer',attacker);
    await staticReject('owner cannot overwrite another issuer root',registry,'setIssuerRoot',[1,123n],'NotIssuer',owner);
    await staticReject('root must be a canonical field element',registry,'setIssuerRoot',[0,FIELD],'InvalidField',signers[0]);
    await staticReject('unchanged issuer root cannot churn epoch',registry,'setIssuerRoot',[0,fixtures.issuerRoots[0]],'Unchanged',signers[0]);
    await staticReject('nonowner cannot change policy',registry,'updatePolicy',[fixtures.policyRoot,2,60],'NotOwner',attacker);
    await staticReject('untrusted account cannot revoke public ID',registry,'revokePublic',[101],'InactiveIssuer',attacker);

    for(const variant of ['signed_direct','signed_cache']) {
      const gate=gates[variant],nonce=await gate.nonces(holderAddress);
      await reject(`${variant}: old nonce replay`,gate,'depositSigned',[credential,signature,AMOUNT,0n],'InvalidNonce',{variant});
      await reject(`${variant}: wrong holder`,gate,'depositSigned',[credential,signature,AMOUNT,0n],'WrongHolder',{variant,signer:attacker});
      await reject(`${variant}: zero amount`,gate,'depositSigned',[credential,signature,0n,nonce],'InvalidAmount',{variant});
      await reject(`${variant}: truncated signature`,gate,'depositSigned',[credential,'0x1234',AMOUNT,nonce],'InvalidSignatureLength',{variant});
      await reject(`${variant}: inactive signer`,gate,'depositSigned',[credential,await sign(credential,attacker),AMOUNT,nonce],'InactiveIssuer',{variant});
      const expired={...credential,validUntil:fixtureTime-1n};
      await reject(`${variant}: expired credential`,gate,'depositSigned',[expired,await sign(expired),AMOUNT,nonce],'CredentialExpired',{variant});
      const futureCredential={...credential,validFrom:(await now())+100000n};
      await reject(`${variant}: not-yet-valid credential`,gate,'depositSigned',[futureCredential,await sign(futureCredential),AMOUNT,nonce],'CredentialNotYetValid',{variant});
      const denied={...credential,eligible:false};
      await reject(`${variant}: signed denial`,gate,'depositSigned',[denied,await sign(denied),AMOUNT,nonce],'Ineligible',{variant});
      const oldPolicy={...credential,policyVersion:0n};
      await reject(`${variant}: policy version mismatch`,gate,'depositSigned',[oldPolicy,await sign(oldPolicy),AMOUNT,nonce],'WrongPolicyVersion',{variant});
      const badDomain=await sign(credential,signers[0],{verifyingContract:await gate.getAddress()});
      await reject(`${variant}: wrong signature domain`,gate,'depositSigned',[credential,badDomain,AMOUNT,nonce],'InactiveIssuer',{variant});
      const badChain=await sign(credential,signers[0],{chainId:chainId+1n});
      await reject(`${variant}: wrong signature chain`,gate,'depositSigned',[credential,badChain,AMOUNT,nonce],'InactiveIssuer',{variant});
    }
    for(const variant of ['zk_direct','zk_cache']) {
      const gate=gates[variant],nonce=await gate.nonces(holderAddress);
      const p=await proofFor(gate,AMOUNT,nonce,{label:`${variant}/negative-control`});
      assert.equal(await verifier.verifyProof(p.tuple[0],p.tuple[1],p.tuple[2],p.tuple[3]),true);
      const outOfField=structuredClone(p.tuple[3]);outOfField[0]=FIELD.toString();
      assert.equal(await verifier.verifyProof(p.tuple[0],p.tuple[1],p.tuple[2],outOfField),false);
      assert.equal(await verifier.verifyProof([1n,1n],p.tuple[1],p.tuple[2],p.tuple[3]),false);
      check(`${variant}: generated verifier returns false for malformed point and out-of-field public input`);
      await reject(`${variant}: old nonce replay`,gate,'depositZK',[p.tuple,AMOUNT,0n],'InvalidNonce',{variant});
      await reject(`${variant}: proof copied to different wallet`,gate,'depositZK',[p.tuple,AMOUNT,0n],'InvalidPublicSignals',{variant,signer:attacker});
      await reject(`${variant}: zero amount`,gate,'depositZK',[p.tuple,0n,nonce],'InvalidAmount',{variant});
      for(const [name,index] of [['registry root',1],['policy root',2],['minimum tier',3],['scope',6],['request',7]]) {
        const changed=structuredClone(p.tuple);changed[3][index]=(BigInt(changed[3][index])+1n).toString();
        await reject(`${variant}: altered ${name}`,gate,'depositZK',[changed,AMOUNT,nonce],'InvalidPublicSignals',{variant});
      }
      const rebound=structuredClone(p.tuple);
      rebound[3][7]=(await gate.computeRequestHash(holderAddress,AMOUNT+1n,nonce,BigInt(rebound[3][4]),BigInt(rebound[3][5]))).toString();
      assert.equal(await snarkjs.groth16.verify(vkey,[...p.publicSignals.slice(0,7),rebound[3][7]],p.proof),false,
        'request public signal must be cryptographically bound, not merely checked by gate');
      await reject(`${variant}: changing public request cannot rebind proof`,gate,'depositZK',[rebound,AMOUNT+1n,nonce],'InvalidProof',{variant});
      const corrupt=structuredClone(p.tuple);corrupt[0]=['0','0'];
      await reject(`${variant}: corrupted proof`,gate,'depositZK',[corrupt,AMOUNT,nonce],'InvalidProof',{variant});
      const toFresh=await proofFor(gate,AMOUNT,0n,{wallet:freshAddress,label:`${variant}/nullifier-wallet-conflict`});
      await reject(`${variant}: same scope pseudonym cannot migrate wallet`,gate,'depositZK',[toFresh.tuple,AMOUNT,0n],
        'NullifierAlreadyBound',{variant,signer:fresh});
      const future=await proofFor(gate,AMOUNT,nonce,{windowStart:(await now())+10000n,windowEnd:(await now())+20000n,label:'future-window'});
      await reject(`${variant}: not-yet-valid authorization window`,gate,'depositZK',[future.tuple,AMOUNT,nonce],'InvalidWindow',{variant});
      const tooLong=await proofFor(gate,AMOUNT,nonce,{windowEnd:(await now())+fixtures.maxTTL+10000n,label:'oversized-window'});
      await reject(`${variant}: authorization exceeds maxTTL`,gate,'depositZK',[tooLong.tuple,AMOUNT,nonce],'InvalidWindow',{variant});
    }
    for(const variant of ['signed_direct','zk_direct']) await staticReject(`${variant}: cache unavailable`,gates[variant],
      'depositCached',[AMOUNT,await gates[variant].nonces(holderAddress)],'CacheDisabled');
    for(const variant of ['signed_cache','zk_cache']) {
      await staticReject(`${variant}: fresh wallet has no authorization`,gates[variant],'depositCached',[AMOUNT,0n],'NoCachedAuthorization',fresh);
      await reject(`${variant}: cached replay`,gates[variant],'depositCached',[AMOUNT,0n],'InvalidNonce',{variant});
    }

    // Snapshot cases isolate epoch/expiry tests without contaminating subsequent
    // cost measurements or changing the fixture's published roots.
    async function snapshotCase(fn) {const id=await rpc.request({method:'evm_snapshot',params:[]});try{await fn();}finally{assert(await rpc.request({method:'evm_revert',params:[id]}));}}
    await snapshotCase(async()=>{
      await record(await registry.updatePolicy(fixtures.policyRoot,3,fixtures.maxTTL),'diagnostic','policy_change',0,{},false);
      for(const variant of ['signed_cache','zk_cache']) await staticReject(`${variant}: policy update invalidates cache`,gates[variant],
        'depositCached',[AMOUNT,await gates[variant].nonces(holderAddress)],'StaleAuthorization');
      await staticReject('old signed policy rejected after change',gates.signed_direct,'depositSigned',
        [credential,signature,AMOUNT,await gates.signed_direct.nonces(holderAddress)],'WrongPolicyVersion');
    });
    await snapshotCase(async()=>{
      const expiry=(await gates.zk_cache.caches(holderAddress)).until;
      await rpc.request({method:'evm_setNextBlockTimestamp',params:[Number(expiry)]});await rpc.request({method:'evm_mine',params:[]});
      assert.equal(await now(),expiry);
      await staticReject('zk cache rejected exactly at expiry',gates.zk_cache,'depositCached',
        [AMOUNT,await gates.zk_cache.nonces(holderAddress)],'AuthorizationExpired');
    });
    await snapshotCase(async()=>{
      const expiry=(await gates.signed_cache.caches(holderAddress)).until;
      await rpc.request({method:'evm_setNextBlockTimestamp',params:[Number(expiry)]});await rpc.request({method:'evm_mine',params:[]});
      assert.equal(await now(),expiry);
      await staticReject('signed cache rejected exactly at expiry',gates.signed_cache,'depositCached',
        [AMOUNT,await gates.signed_cache.nonces(holderAddress)],'AuthorizationExpired');
    });

    // Token failures must undo nonce, deposit, cache, and nullifier registration.
    const adversary=await deploy('contracts/AdversarialToken.sol','AdversarialToken',
      [holderAddress,ethers.parseUnits('100000',18)],'diagnostic','deploy_adversarial_token',false);
    for(const variant of ['signed_cache','zk_cache']) {
      const gate=(await deploy('contracts/AccessGate.sol','AccessGate',
        [await registry.getAddress(),await adversary.getAddress(),await verifier.getAddress(),isZK(variant),true],
        'diagnostic','deploy_adversarial_gate',false)).connect(holder);
      await (await adversary.connect(holder).approve(await gate.getAddress(),ethers.MaxUint256)).wait();
      const p=isZK(variant)?await proofFor(gate,AMOUNT,0n,{label:`${variant}/token-failure-control`}):null;
      const method=isZK(variant)?'depositZK':'depositSigned';
      const args=isZK(variant)?[p.tuple,AMOUNT,0n]:[credential,signature,AMOUNT,0n];
      await (await adversary.setFailureMode(1)).wait();
      await reject(`${variant}: false token return rolls back authorization`,gate,method,args,'TokenTransferFailed',{asset:adversary,variant});
      await (await adversary.setFailureMode(2)).wait();
      await reject(`${variant}: reverting token rolls back authorization`,gate,method,args,'DeliberateTransferFailure',{asset:adversary,variant});
      await (await adversary.setFailureMode(0)).wait();
      await (await adversary.setReentry(await gate.getAddress(),gate.interface.encodeFunctionData('depositCached',[AMOUNT,0n]),true,false)).wait();
      const before=await state(gate,holderAddress,adversary);
      await record(await gate[method](...args),'diagnostic','blocked_reentry_outer_deposit',0,{},false);
      assert.equal(await adversary.lastReentrySuccess(),false);
      assert.equal(gate.interface.parseError(await adversary.lastReentryResult()).name,'Reentrancy');
      const after=await state(gate,holderAddress,adversary);
      assert.equal(after.nonce,before.nonce+1n);assert.equal(after.deposit,before.deposit+AMOUNT);
      assert.equal(after.holderBalance,before.holderBalance-AMOUNT);assert.equal(after.gateBalance,before.gateBalance+AMOUNT);
      check(`${variant}: reentrant inner deposit rejected; outer transfer occurs once`);
      await (await adversary.setReentry(ethers.ZeroAddress,'0x',false,false)).wait();
    }

    // Register deliberately invalid credentials so predicate tests are not just
    // failures of a stale credential-commitment opening.
    const originalSecondary={...fixtures.credentials[0][1]};
    for(const [name,patch] of [['insufficient tier',{tier:1n}],['forbidden jurisdiction',{jurisdiction:99n}],
      ['expired credential',{credentialExpiry:fixtureTime-1n}],['not-yet-valid credential',{notBefore:(await now())+100000n}]]) {
      const badRoot=fixtures.setCredential(0,1,{...originalSecondary,...patch});
      await (await registry.connect(signers[0]).setIssuerRoot(0,badRoot)).wait();
      assert.equal(await registry.registryRoot(),fixtures.registryRoot);
      await assert.rejects(()=>proofFor(gates.zk_direct,AMOUNT,undefined,{credentialIndex:1,label:`invalid-${name}`}));
      check(`circuit rejects registered ${name}`,{phase:'witness_generation',gas_used:0});
    }
    await (await registry.connect(signers[0]).setIssuerRoot(0,fixtures.setCredential(0,1,originalSecondary))).wait();
    const malformedInput=fixtures.inputFor({scope:await gates.zk_direct.computeScope(),requestHash:123n,
      windowStart:await now(),windowEnd:(await now())+fixtures.maxTTL});
    malformedInput.credentialDirections[0]='2';
    await assert.rejects(()=>fullProof(malformedInput,'nonboolean-path',chain));
    check('circuit rejects a nonboolean Merkle direction',{phase:'witness_generation',gas_used:0});

    // Revocation mechanisms are paired explicitly; they are different storage
    // representations of the same scenario, not an implicit cross-format map.
    for(const variant of ['signed_cache','zk_cache']) await successful(variant,'diagnostic_reauthorize',0,{measured:false});
    await (await registry.connect(signers[0]).revokePublic(credential.id)).wait();
    await staticReject('public credential revocation rejects signed access',gates.signed_direct,'depositSigned',
      [credential,signature,AMOUNT,await gates.signed_direct.nonces(holderAddress)],'CredentialRevoked');
    for(const variant of ['signed_cache','zk_cache']) await staticReject(`${variant}: public revocation invalidates a current cache`,gates[variant],
      'depositCached',[AMOUNT,await gates[variant].nonces(holderAddress)],'StaleAuthorization');
    const beforeRevocation=await proofFor(gates.zk_direct,AMOUNT,undefined,{label:'public-revocation-does-not-remove-hidden-leaf'});
    await gates.zk_direct.depositZK.staticCall(beforeRevocation.tuple,AMOUNT,await gates.zk_direct.nonces(holderAddress));
    check('public ID revocation alone leaves active hidden credential provable; separate issuer-root removal required');
    await successful('zk_cache','diagnostic_reauthorize',0,{measured:false});
    await (await registry.connect(signers[0]).setIssuerRoot(0,fixtures.removeCredential(0,0))).wait();
    await staticReject('removed credential invalidates old membership proof',gates.zk_direct,'depositZK',
      [beforeRevocation.tuple,AMOUNT,await gates.zk_direct.nonces(holderAddress)],'InvalidPublicSignals');
    await assert.rejects(()=>proofFor(gates.zk_direct,AMOUNT,undefined,{label:'removed-credential'}));
    check('removed credential cannot produce current-root witness',{phase:'witness_generation',gas_used:0});
    for(const variant of ['signed_cache','zk_cache']) await staticReject(`${variant}: revocation cannot use old cache`,gates[variant],
      'depositCached',[AMOUNT,await gates[variant].nonces(holderAddress)],'StaleAuthorization');
    await (await registry.disableIssuer(0)).wait();
    await staticReject('disabled issuer cannot republish root',registry,'setIssuerRoot',[0,123n],'InactiveIssuer',signers[0]);
    await staticReject('disabled issuer rejected for signed access',gates.signed_direct,'depositSigned',
      [credential,signature,AMOUNT,await gates.signed_direct.nonces(holderAddress)],'InactiveIssuer');

    environments.push({chain,chain_id:chainId,chain_type:connection.chainType,hardfork:connection.networkConfig.hardfork,
      runtime:'Hardhat EDR in-memory simulation',initial_timestamp:fixtureTime,
      addresses:{registry:await registry.getAddress(),token:await token.getAddress(),verifier:await verifier.getAddress(),
        hasher:await hasher.getAddress(),holder:holderAddress,gates:Object.fromEntries(await Promise.all(VARIANTS.map(async v=>[v,await gates[v].getAddress()])))} });
    console.log(`${chain}: completed ${tests.filter(t=>t.chain===chain).length} integration/security checks`);
  } finally {await connection.close();}
}

// Always refresh this fixture for the exact current circuit and benchmark setup.
if(fs.existsSync('build/browser_input.json')) fs.unlinkSync('build/browser_input.json');
for(const chain of CHAINS) await runChain(chain);
const sourceFiles=['package.json','package-lock.json','hardhat.config.js','circuits/access.circom',
  'contracts/AccessRegistry.sol','contracts/AccessGate.sol','contracts/MockToken.sol','contracts/AdversarialToken.sol',
  'scripts/fixtures.mjs','scripts/setup.mjs','scripts/benchmark.mjs'];
const sourceHashes=Object.fromEntries(sourceFiles.map(p=>[p,sha(fs.readFileSync(p))]));
const metadata={recorded_at:new Date().toISOString(),source_sha:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),
  source_dirty:!!execFileSync('git',['status','--porcelain','--',...sourceFiles],{encoding:'utf8'}).trim(),
  workspace_has_uncommitted_files:!!execFileSync('git',['status','--porcelain'],{encoding:'utf8'}).trim(),source_files_sha256:sourceHashes,
  source_tree_sha256:sha(json(sourceHashes)),node:process.version,platform:process.platform,arch:process.arch,
  cpu:os.cpus()[0]?.model,logical_cpus:os.cpus().length,memory_bytes:os.totalmem(),
  dependencies:JSON.parse(read('package.json')).dependencies,solc:solc.version(),compiler_settings:compilerSettings,
  bytecode_sha256:Object.fromEntries(files.flatMap(f=>Object.entries(compiled.contracts[f]).filter(([,a])=>a.evm.bytecode.object)
    .map(([name,a])=>[`${f}:${name}`,sha(a.evm.bytecode.object)]))),setup,environments,synthetic:true,
  sample_count_warm:RUNS,production_sample_count:30,debug_run:RUNS!==30||CHAINS.length!==2,
  variants:VARIANTS,credential_depth:10,issuer_depth:2,policy_depth:3,issuer_slots:4,
  validity_days:90,max_authorization_days:30,deposit_amount:'100',token:'Mock Test EUR; 18 decimals; no monetary value',
  public_signals:['scopeNullifier','registryRoot','policyRoot','minTier','windowStart','windowEnd','scope','requestHash'],
  proof_timing_boundary:'fullProve: file reads + witness + Groth16 proving; singleThread=true. Strict offchain verify separately. Warm sequential samples are one process, not independent devices.',
  sampling:`One first action, ${RUNS} warmed repeated actions per variant and chain; ${RUNS} authenticated root updates and reauthorizations per cached variant. Diagnostic proofs excluded from cost samples.`,
  assumptions:['Shared gate token balance preseeded once; first access means first HOLDER state, not first service receipt.',
    'Unlimited token allowance; returning-user state preserved for repeat samples.',
    'The same compiled Cancun-target bytecode executes under L1 Osaka and OP Isthmus rules.',
    'OP gas is local execution only. L1 data-availability and operator fees require separate sourced inputs.',
    'Global registry epochs invalidate all cached authorizations, including unrelated credential updates.',
    'Public signed-ID revocation and hidden credential removal are separate updates, explicitly paired in tests.',
    'Issuer roots authenticate issuer authority, not real-world truth of KYC claims.',
    'Fixtures expose deterministic holder secrets; no personal information is protected by these public examples.',
    'Public phase1 transcript; local phase2 contributions are not independent and are not production-safe.',
    'Stable application nullifiers and public wallets/actions remain linkable; no end-to-end unlinkability claim.',
    'No actual RPC network latency, wallet UX, issuer service, real funds, production deployment or adoption estimate.']};
write('results/measurements.json',{schema_version:2,metadata,events});
write('results/test_results.json',{schema_version:2,source_tree_sha256:metadata.source_tree_sha256,passed:tests.length,failed:0,tests});
write('results/transactions.json',transactions);
write('results/proof_samples.json',{schema_version:2,samples:proofSamples});
// Retain the exact verification artifacts for archived randomized proofs.
// Re-running phase 2 produces a different key; hashes alone cannot verify them.
fs.mkdirSync('results/cryptographic_artifacts',{recursive:true});
for(const name of ['verification_key.json','Verifier.sol','setup.json','browser_input.json'])
  fs.copyFileSync(`build/${name}`,`results/cryptographic_artifacts/${name}`);
console.log(`PASS ${tests.length} checks; wrote ${events.length} measured events (${RUNS} warm samples).`);
// snarkjs worker pools can remain alive after awaited work has finished.
process.exit(0);
