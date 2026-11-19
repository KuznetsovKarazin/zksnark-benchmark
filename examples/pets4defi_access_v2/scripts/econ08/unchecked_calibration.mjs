// ECON-08 v0.5: matched common-deposit calibration, no eligibility checks.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {gzipSync} from 'node:zlib';
import {network} from 'hardhat';
import {ethers} from 'ethers';
import solc from 'solc';

process.chdir(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..'));
const output = process.argv[2];
assert(output, 'Supply a new output directory');
fs.mkdirSync(output, {recursive: false});
const hash = b => createHash('sha256').update(b).digest('hex');
const json = x => JSON.stringify(x, (_,v) => typeof v === 'bigint' ? String(v) : v, 2)+'\n';
const files = ['contracts/MockToken.sol','contracts/UncheckedDeposit.sol'];
const settings = {optimizer:{enabled:true,runs:200},evmVersion:'cancun',outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}};
const compiled = JSON.parse(solc.compile(json({language:'Solidity',settings,
  sources:Object.fromEntries(files.map(f=>[f,{content:fs.readFileSync(f,'utf8')}]))})));
assert.equal((compiled.errors??[]).filter(e=>e.severity==='error').length,0);
const evidence={schema:'ECON08_UNCHECKED_V05',status:'RUNNING',created_utc:new Date().toISOString(),
  source_commit:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),
  source_hashes:Object.fromEntries([...files,'package-lock.json','hardhat.config.js','scripts/econ08/unchecked_calibration.mjs'].map(f=>[f,hash(fs.readFileSync(f))])),
  environment:{node:process.version,solc:solc.version(),settings,hardfork:'osaka',chain_id:31337},
  design:{A:4,accesses_per_holder:100,horizon:90*86400,amount:'100000000000000000000',bootstrap_per_gate:'1',
    groups:[1,2,4],eligibility:'absent',approval:'max allowance; observed actual gas',
    limitations:['Matched deposit state/workload, not same deployment address or calldata as the eligibility gates.',
      'No new ZK, paymaster, population-scaling or A32 measurement.','Shared costs are not allocated to K05/K06.']},runs:[]};
const amount=ethers.parseUnits('100',18);
try {
for(const B of [1,2,4]){
  const connection=await network.create({network:'l1',override:{allowBlocksWithSameTimestamp:true}});
  const rpc=connection.provider,provider=new ethers.BrowserProvider(rpc,undefined,{cacheTimeout:-1});provider.pollingInterval=10;
  const signers=await Promise.all(Array.from({length:9},(_,i)=>provider.getSigner(i)));
  const addresses=await Promise.all(signers.map(s=>s.getAddress()));
  const base=Number((await provider.getBlock('latest')).timestamp)+3600;
  const run={B,base,transactions:[],accesses:[],holders:addresses.slice(5,9)};evidence.runs.push(run);
  async function record(tx,category,actor,extra={}){
    const r=await tx.wait();assert.equal(r.status,1);
    const t=ethers.Transaction.from(tx.toJSON());assert.equal(t.hash,r.hash);assert.equal(t.from,tx.from);
    const timestamp=Number((await provider.getBlock(r.blockNumber)).timestamp);
    const row={category,actor,...extra,timestamp,gas:Number(r.gasUsed),receipt:r.toJSON(),transaction:tx.toJSON(),signed_serialized:t.serialized};
    run.transactions.push(row);return row;
  }
  async function deploy(file,name,args,category){const c=compiled.contracts[file][name];
    const a=await new ethers.ContractFactory(c.abi,c.evm.bytecode.object,signers[0]).deploy(...args);
    await record(a.deploymentTransaction(),category,'operator');await a.waitForDeployment();return a;}
  try{
    const token=await deploy(files[0],'MockToken',[addresses[5],ethers.parseUnits('10000000',18)],'excluded_mock_deployment');
    const gates=[];for(let g=0;g<B;g++)gates.push(await deploy(files[1],'UncheckedDeposit',[token.target],'shared_unchecked_deployment'));
    for(let g=0;g<B;g++)await record(await token.connect(signers[5]).transfer(gates[g].target,1n),'excluded_bootstrap','holder_0');
    for(let h=0;h<4;h++){
      const group=Math.floor(h/(4/B));
      if(h)await record(await token.connect(signers[5]).transfer(addresses[5+h],amount*100n+1n),'excluded_fixture_funding',`holder_${h}`);
      await record(await token.connect(signers[5+h]).approve(gates[group].target,ethers.MaxUint256),'approval',`holder_${h}`,{group});
    }
    for(let i=0;i<100;i++)for(let h=0;h<4;h++){
      const group=Math.floor(h/(4/B)),g=gates[group].connect(signers[5+h]),holder=addresses[5+h];
      const timestamp=base+Math.floor(i*90*86400/100);
      const before={nonce:await g.nonces(holder),deposit:await g.deposits(holder),holder_balance:await token.balanceOf(holder),gate_balance:await token.balanceOf(g.target)};
      assert.equal(before.nonce,BigInt(i));
      await rpc.request({method:'evm_setNextBlockTimestamp',params:[timestamp]});
      const tx=await record(await g.deposit(amount,BigInt(i)),'access',`holder_${h}`,{group,index:i});
      assert.equal(tx.timestamp,timestamp);
      const after={nonce:await g.nonces(holder),deposit:await g.deposits(holder),holder_balance:await token.balanceOf(holder),gate_balance:await token.balanceOf(g.target)};
      assert.equal(after.nonce,before.nonce+1n);assert.equal(after.deposit,before.deposit+amount);
      assert.equal(after.holder_balance,before.holder_balance-amount);assert.equal(after.gate_balance,before.gate_balance+amount);
      run.accesses.push({holder:h,index:i,at:timestamp-base,gas:tx.gas,tx_hash:tx.receipt.hash,before,after});
    }
    // A wrong nonce must revert and leave protected state unchanged.
    for(let h=0;h<4;h++){
      const g=gates[Math.floor(h/(4/B))].connect(signers[5+h]);
      await assert.rejects(g.deposit.staticCall(amount,99n),e=>e.revert?.name==='InvalidNonce');
      assert.equal(await g.nonces(addresses[5+h]),100n);
    }
    const gas=c=>run.transactions.filter(t=>t.category===c).reduce((s,t)=>s+t.gas,0);
    run.summary={approval_gas:gas('approval'),access_gas:gas('access'),common_K05_gas:gas('approval')+gas('access'),
      access_count:run.accesses.length,shared_unchecked_deployment_gas:gas('shared_unchecked_deployment'),negative_nonce_checks:4};
    console.log(JSON.stringify({B,...run.summary}));
  }finally{await connection.close();}
}
evidence.status='PASS';
}catch(e){evidence.status='FAIL';evidence.error=e.stack;process.exitCode=1;}
fs.writeFileSync(path.join(output,'receipts.json.gz'),gzipSync(json(evidence),{mtime:0}));
const report={...evidence,runs:evidence.runs.map(({transactions,accesses,...r})=>({...r,transaction_count:transactions.length}))};
fs.writeFileSync(path.join(output,'report.json'),json(report));
fs.writeFileSync(path.join(output,'SHA256SUMS'),['report.json','receipts.json.gz'].map(f=>hash(fs.readFileSync(path.join(output,f)))+'  '+f).join('\n')+'\n');
if(evidence.status!=='PASS')console.error(evidence.error);
