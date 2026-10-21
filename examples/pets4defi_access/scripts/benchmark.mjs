import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';
import { performance } from 'node:perf_hooks';
import ganache from 'ganache';
import solc from 'solc';
import * as snarkjs from 'snarkjs';
import { buildPoseidon } from 'circomlibjs';
import { ethers } from 'ethers';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
process.chdir(root);
const read = p => fs.readFileSync(p, 'utf8');
const sha = data => createHash('sha256').update(data).digest('hex');
const json = x => JSON.stringify(x, (_, v) => typeof v === 'bigint' ? v.toString() : v, 2) + '\n';
const write = (p, x) => fs.writeFileSync(p, json(x));
const FIELD = 21888242871839275222246405745257275088548364400416034343698204186575808495617n;
const CHAIN = 31337;
const REPEATS = 5;
const events = [], tests = [], transactions = [];
fs.mkdirSync('results/proofs', { recursive: true });
const setup = JSON.parse(read('build/setup.json'));
for (const [key,p] of Object.entries({circuit_sha256:'circuits/eligible.circom',lock_sha256:'package-lock.json',zkey_sha256:'build/eligible_final.zkey',wasm_sha256:'build/eligible_js/eligible.wasm',verifier_sha256:'build/Verifier.sol',verification_key_sha256:'build/verification_key.json'})) {
  assert.equal(setup[key],sha(fs.readFileSync(p)),`Stale or altered setup artifact ${p}; run npm run setup`);
}
const vkey = JSON.parse(read('build/verification_key.json'));
const sources = Object.fromEntries(['contracts/AccessGate.sol', 'contracts/MockToken.sol', 'build/Verifier.sol'].map(p => [p, {content: read(p)}]));
const settings = { optimizer: { enabled: true, runs: 200 }, evmVersion: 'shanghai', outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object', 'evm.deployedBytecode.object'] } } };
const compiled = JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources,settings})));
const errors = (compiled.errors || []).filter(e => e.severity === 'error');
assert.equal(errors.length, 0, errors.map(e => e.formattedMessage).join('\n'));
const artifact = (file, name) => compiled.contracts[file][name];

// Ganache keys are public, deterministic fixtures. Never use them with real assets.
const rpc = ganache.provider({logging:{quiet:true},chain:{chainId:CHAIN,hardfork:'shanghai',time:new Date('2026-10-20T12:00:00Z')},wallet:{deterministic:true,totalAccounts:5},miner:{timestampIncrement:1}});
const provider = new ethers.BrowserProvider(rpc, undefined, {cacheTimeout:-1});
provider.pollingInterval = 10;
const deployer = await provider.getSigner(0), holder = await provider.getSigner(1), attacker = await provider.getSigner(2);
const issuer = new ethers.Wallet(Object.values(rpc.getInitialAccounts())[0].secretKey);
const fakeIssuer = new ethers.Wallet(Object.values(rpc.getInitialAccounts())[2].secretKey);
const holderAddress = await holder.getAddress();
const issuerAddress = issuer.address;
const amount = ethers.parseUnits('100',18);
const poseidon = await buildPoseidon();
const age = 25n;
const salt = BigInt('0x'+sha('PETs4DeFi synthetic fixture, not a user secret')) % FIELD;
const commitment = poseidon.F.toObject(poseidon([age,salt]));

async function record(tx, variant, event, run=0, extra={}) {
  const receipt = await tx.wait();
  assert.equal(receipt.status,1);
  transactions.push({variant,event,run,receipt:receipt.toJSON()});
  events.push({variant,event,run,gas_used:Number(receipt.gasUsed),proof_time_ms:null,offchain_verify_ms:null,tx_hash:receipt.hash,evidence_status:'measured_local',scope:event.startsWith('deploy_')||event==='bootstrap_token_balance'?'shared_fixed':event==='revoke'?'per_credential':'per_action',...extra});
  return receipt;
}
async function deploy(file,name,args,variant,event) {
  const a=artifact(file,name);
  const c=await new ethers.ContractFactory(a.abi,a.evm.bytecode.object,deployer).deploy(...args);
  await record(c.deploymentTransaction(),variant,event);
  await c.waitForDeployment();
  return c;
}
const token=await deploy('contracts/MockToken.sol','MockToken',[holderAddress,ethers.parseUnits('100000',18)],'shared','deploy_token');
const verifierName=Object.keys(compiled.contracts['build/Verifier.sol']).find(k=>compiled.contracts['build/Verifier.sol'][k].evm.bytecode.object);
const verifier=await deploy('build/Verifier.sol',verifierName,[],'zk','deploy_verifier');
const gates={};
for (const variant of ['baseline','zk']) {
  gates[variant]=(await deploy('contracts/AccessGate.sol','AccessGate',[issuerAddress,await token.getAddress(),await verifier.getAddress(),variant==='zk'],variant,'deploy_gate')).connect(holder);
  // The gate's token balance is shared service state, not a per-new-user slot.
  // Initialize it once so first-deposit gas only captures new HOLDER state.
  await record(await token.connect(holder).transfer(await gates[variant].getAddress(),1n),variant,'bootstrap_token_balance');
  await record(await token.connect(holder).approve(await gates[variant].getAddress(),ethers.MaxUint256),variant,'approve');
}
const tokenAddress=await token.getAddress();
const baseTime=Number((await provider.getBlock('latest')).timestamp);
const expiry=baseTime+90*86400;
const credentials={baseline:{holder:holderAddress,credentialId:101n,validUntil:expiry,eligible:true},zk:{holder:holderAddress,credentialId:101n,validUntil:expiry,commitment}};
const types={baseline:{BaselineCredential:[{name:'holder',type:'address'},{name:'credentialId',type:'uint256'},{name:'validUntil',type:'uint64'},{name:'eligible',type:'bool'}]},zk:{PrivateCredential:[{name:'holder',type:'address'},{name:'credentialId',type:'uint256'},{name:'validUntil',type:'uint64'},{name:'commitment',type:'uint256'}]}};
async function domain(variant,overrides={}) {return {name:'PETs4DeFiAccess',version:'1',chainId:CHAIN,verifyingContract:await gates[variant].getAddress(),...overrides};}
async function sign(variant,credential=credentials[variant],wallet=issuer,overrides={}) {return wallet.signTypedData(await domain(variant,overrides),types[variant],credential);}
const signatures={baseline:await sign('baseline'),zk:await sign('zk')};
for (const variant of ['baseline','zk']) {
  const digest=ethers.TypedDataEncoder.hash(await domain(variant),types[variant],credentials[variant]);
  assert.equal(digest,await gates[variant][variant==='zk'?'hashPrivateCredential':'hashBaselineCredential'](credentials[variant]));
  tests.push({name:`${variant}: EIP712 digest matches independently encoded digest`,passed:true});
}
function requestHash(gateAddress,credential,depositAmount,nonce,chainId=CHAIN) {
  return BigInt(ethers.keccak256(ethers.AbiCoder.defaultAbiCoder().encode(['uint256','address','address','address','uint256','uint256','uint256','uint64'],[chainId,gateAddress,credential.holder,tokenAddress,depositAmount,nonce,credential.credentialId,credential.validUntil])))%FIELD;
}
async function prove(credential=credentials.zk,depositAmount=amount,nonce=0n,overrides={}) {
  const request=requestHash(await gates.zk.getAddress(),credential,depositAmount,nonce);
  assert.equal(request,await gates.zk.computeRequestHash(credential.holder,depositAmount,nonce,credential.credentialId,credential.validUntil));
  const input={age:age.toString(),salt:salt.toString(),commitment:credential.commitment.toString(),requestHash:request.toString(),...overrides};
  const start=performance.now();
  const {proof,publicSignals}=await snarkjs.groth16.fullProve(input,'build/eligible_js/eligible.wasm','build/eligible_final.zkey',undefined,undefined,{singleThread:true});
  const proofTime=performance.now()-start;
  const vstart=performance.now();
  assert.equal(await snarkjs.groth16.verify(vkey,publicSignals,proof),true,'strict offchain verification');
  const verifyTime=performance.now()-vstart;
  const [a,b,c,signals]=JSON.parse('['+await snarkjs.groth16.exportSolidityCallData(proof,publicSignals)+']');
  assert.equal(BigInt(signals[1]),BigInt(input.commitment));
  assert.equal(BigInt(signals[2]),BigInt(input.requestHash));
  return {tuple:[a,b,c,signals],proof,publicSignals,input,proofTime,verifyTime};
}
async function state(variant) {
  const gate=gates[variant],address=await gate.getAddress();
  return {nonce:await gate.nonces(holderAddress),deposit:await gate.deposits(holderAddress),holderBalance:await token.balanceOf(holderAddress),gateBalance:await token.balanceOf(address)};
}
function deposit(variant,credential,signature,depositAmount,nonce,p,signer=holder,options={}) {
  const g=gates[variant].connect(signer);
  return variant==='zk'?g.depositPrivate(credential,signature,depositAmount,nonce,p,options):g.depositBaseline(credential,signature,depositAmount,nonce,options);
}
const successfulProofs=[];
for (let run=0;run<=REPEATS;run++) {
  for (const variant of ['baseline','zk']) {
    const before=await state(variant);
    const p=variant==='zk'?await prove(credentials.zk,amount,before.nonce):null;
    if (p) {successfulProofs.push(p);write(`results/proofs/valid-${run}.json`,p);}
    const tx=await deposit(variant,credentials[variant],signatures[variant],amount,before.nonce,p?.tuple);
    const receipt=await record(tx,variant,run===0?'deposit_first':'deposit_repeat',run,{proof_time_ms:p?.proofTime??null,offchain_verify_ms:p?.verifyTime??null});
    const after=await state(variant);
    assert.deepEqual(after,{nonce:before.nonce+1n,deposit:before.deposit+amount,holderBalance:before.holderBalance-amount,gateBalance:before.gateBalance+amount});
    tests.push({name:`${variant}: successful deposit ${run}, token transfer and nonce`,passed:true,tx_hash:receipt.hash});
    console.log(`${variant} ${run===0?'first':'repeat '+run}: ${receipt.gasUsed} gas${p?', prove '+p.proofTime.toFixed(1)+' ms':''}`);
  }
}

// Every rejection uses a current nonce and otherwise valid material, except the
// field explicitly under test. Static calls check the cause; included reverted
// transactions establish nonzero failure gas and unchanged state.
async function reject(name,variant,args,expectedError) {
  const before=await state(variant);
  const {credential=credentials[variant],signature=signatures[variant],depositAmount=amount,nonce=before.nonce,proof=nextProof.tuple,signer=holder}=args;
  const gate=gates[variant].connect(signer);
  const method=variant==='zk'?'depositPrivate':'depositBaseline';
  const callArgs=variant==='zk'?[credential,signature,depositAmount,nonce,proof]:[credential,signature,depositAmount,nonce];
  let reason;
  try {await gate[method].staticCall(...callArgs);assert.fail('invalid call unexpectedly accepted');}
  catch(e) {
    if (e.code!=='CALL_EXCEPTION') throw e;
    reason=e.revert?.name;
    if (!reason && e.data) {try{reason=gate.interface.parseError(e.data)?.name;}catch{}}
    assert.equal(reason,expectedError,`${name}: unexpected rejection cause`);
  }
  let receipt;
  try {const tx=await deposit(variant,credential,signature,depositAmount,nonce,proof,signer,{gasLimit:1000000n});await tx.wait();assert.fail('invalid transaction accepted');}
  catch(e){if(e.code!=='CALL_EXCEPTION'||!e.receipt)throw e;receipt=e.receipt;assert.equal(receipt.status,0);}
  assert.deepEqual(await state(variant),before,`${name}: failure changed state`);
  transactions.push({variant,event:'negative',name,receipt:receipt.toJSON()});
  tests.push({name:`${variant}: ${name}`,passed:true,expected_error:expectedError,gas_used:Number(receipt.gasUsed),tx_hash:receipt.hash,state_unchanged:true});
}
const nextNonce=await gates.zk.nonces(holderAddress);
const nextProof=await prove(credentials.zk,amount,nextNonce);
for (const variant of ['baseline','zk']) {
  await reject('replay old nonce',variant,{nonce:0n,proof:successfulProofs[0].tuple},'InvalidNonce');
  await reject('wrong holder',variant,{signer:attacker},'WrongHolder');
  await reject('zero amount',variant,{depositAmount:0n},'InvalidAmount');
  await reject('untrusted issuer',variant,{signature:await sign(variant,credentials[variant],fakeIssuer)},'InvalidSignature');
  await reject('truncated signature',variant,{signature:'0x1234'},'InvalidSignatureLength');
  await reject('wrong verifying contract in signature',variant,{signature:await sign(variant,credentials[variant],issuer,{verifyingContract:tokenAddress})},'InvalidSignature');
  await reject('wrong chain in signature',variant,{signature:await sign(variant,credentials[variant],issuer,{chainId:CHAIN+1})},'InvalidSignature');
  const expired={...credentials[variant],validUntil:baseTime-1};
  const expiredProof=variant==='zk'?await prove(expired,amount,nextNonce):null;
  await reject('expired credential',variant,{credential:expired,signature:await sign(variant,expired),proof:expiredProof?.tuple},'CredentialExpired');
}
const ineligible={...credentials.baseline,eligible:false};
await reject('issuer signed ineligible credential','baseline',{credential:ineligible,signature:await sign('baseline',ineligible)},'Ineligible');
await reject('different amount with old proof','zk',{depositAmount:amount+1n},'InvalidPublicSignals');
const rebound=structuredClone(nextProof.tuple);
rebound[3][2]=requestHash(await gates.zk.getAddress(),credentials.zk,amount+1n,nextNonce).toString();
await reject('changed request hash cannot rebind old proof','zk',{depositAmount:amount+1n,proof:rebound},'InvalidProof');
const corrupted=structuredClone(nextProof.tuple);corrupted[0]=['0','0'];
await reject('corrupted Groth16 proof','zk',{proof:corrupted},'InvalidProof');
const wrongCommit=structuredClone(nextProof.tuple);wrongCommit[3][1]=(commitment+1n).toString();
await reject('credential commitment differs from proof','zk',{proof:wrongCommit},'InvalidPublicSignals');
for (const [name,overrides] of [['underage',{age:'17'}],['out of 8-bit age range',{age:'256'}],['wrong commitment opening',{salt:(salt+1n).toString()}]]) {
  // For the first two cases issue a commitment matching the bad age so that
  // failure establishes the predicate/range constraint, not a hash mismatch.
  const badAge=overrides.age?BigInt(overrides.age):age;
  const badCredential={...credentials.zk,commitment:overrides.age?poseidon.F.toObject(poseidon([badAge,salt])):commitment};
  await assert.rejects(()=>prove(badCredential,amount,nextNonce,overrides),e=>/Assert Failed/.test(e.message));
  tests.push({name:`zk: witness rejects ${name}`,passed:true,phase:'witness_generation',gas_used:0});
}
for (const variant of ['baseline','zk']) {
  await assert.rejects(()=>gates[variant].connect(attacker).revokeCredential.staticCall(101n),e=>e.code==='CALL_EXCEPTION'&&e.revert?.name==='NotIssuer');
  tests.push({name:`${variant}: nonissuer cannot revoke`,passed:true});
  await record(await gates[variant].connect(deployer).revokeCredential(101n),variant,'revoke');
  await reject('revoked credential',variant,{},'CredentialRevoked');
}

// Expiry is strict: t == validUntil is already invalid. A fresh unrevoked ID
// avoids confusing this boundary test with revocation of the main fixture.
const boundaryProof=await prove({...credentials.zk,credentialId:102n},amount,nextNonce);
await rpc.request({method:'evm_setTime',params:[(expiry)*1000]});
await rpc.request({method:'evm_mine',params:[{timestamp:expiry}]});
assert.equal(Number((await provider.getBlock('latest')).timestamp),expiry);
for (const variant of ['baseline','zk']) {
  const atBoundary={...credentials[variant],credentialId:102n};
  const gate=gates[variant];
  const sig=await sign(variant,atBoundary);
  const args=variant==='zk'?[atBoundary,sig,amount,nextNonce,boundaryProof.tuple]:[atBoundary,sig,amount,nextNonce];
  await assert.rejects(()=>gate[variant==='zk'?'depositPrivate':'depositBaseline'].staticCall(...args),e=>e.code==='CALL_EXCEPTION'&&e.revert?.name==='CredentialExpired');
  tests.push({name:`${variant}: expiry boundary t == validUntil rejected`,passed:true,timestamp:expiry});
}

const sourceFiles=['package.json','package-lock.json','circuits/eligible.circom','contracts/AccessGate.sol','contracts/MockToken.sol','scripts/setup.mjs','scripts/benchmark.mjs','scripts/economics.py','scripts/test_economics.py'];
const sourceHashes=Object.fromEntries(sourceFiles.map(p=>[p,sha(fs.readFileSync(p))]));
const metadata={
  recorded_at:new Date().toISOString(),source_sha:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),source_dirty:!!execFileSync('git',['status','--porcelain','--',...sourceFiles],{encoding:'utf8'}).trim(),source_files_sha256:sourceHashes,
  source_tree_sha256:sha(json(sourceHashes)),node:process.version,platform:process.platform,arch:process.arch,cpu:os.cpus()[0]?.model,logical_cpus:os.cpus().length,memory_bytes:os.totalmem(),
  chain_id:CHAIN,evm:'Ganache 7.9.2; Shanghai hardfork; local in-memory chain',solc:solc.version(),compiler_settings:settings,dependencies:JSON.parse(read('package.json')).dependencies,
  setup,synthetic:true,age:25,predicate:'8-bit age >= 18',signature:'secp256k1 EIP712, checked outside ZK',proof:'Groth16 BN254, 496 constraints',
  public_signals:['actionBinding','commitment','requestHash'],token:'Mock Test EUR, 18 decimals, no monetary value',deposit_amount:'100',validity_days:90,
  addresses:{issuer:issuerAddress,holder:holderAddress,token:tokenAddress,verifier:await verifier.getAddress(),baseline_gate:await gates.baseline.getAddress(),zk_gate:await gates.zk.getAddress()},
  timing_boundary:'fullProve: WASM/key reads + witness generation + Groth16 proving, singleThread=true. Offchain verify separately. No network/issuer/wallet/user latency. First run is cold, later runs sequential.',
  sampling:'One first-holder deposit and five sequential repeat deposits per variant. Shared gate token balance preseeded once and excluded from per-user cost. Pilot, not a population estimate. Six fresh ZK proofs; first process run may be cold, which is independent of new/returning user identity. Negative-test proofs excluded from cost inputs.',
  limitations:['Local Shanghai EVM gas; not current mainnet measurement or monetary quote.','Single-process trusted setup and deterministic public fixture salt/keys: never production.','Stable commitment, holder address, deposit amount, credential ID and expiry remain public/linkable.','Baseline already discloses only an issuer-signed eligibility bit. No automatic privacy superiority claim.','Revocation is per gate and must be propagated; no oracle, issuer service, relayer or full KYC workflow.','Receipt gas includes token transfer, calldata and verification; verifier gas must not be added again.','No withdrawal function. Test tokens only.'],
};
write('results/measurements.json',{schema_version:1,metadata,events});
write('results/test_results.json',{schema_version:1,source_tree_sha256:metadata.source_tree_sha256,passed:tests.length,failed:0,tests});
write('results/transactions.json',transactions);
write('results/fixtures.json',{credentials,signatures,age,salt,commitment});
console.log(`PASS ${tests.length} checks. Wrote ${events.length} measured events to results/measurements.json`);
await rpc.disconnect();
// snarkjs/circomlibjs retain worker pools after all awaited operations finish.
process.exit(0);
