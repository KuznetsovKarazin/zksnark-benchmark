import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {gzipSync} from 'node:zlib';
import {prepare,context,json,hash,sourceFiles} from './harness.mjs';
import {pilotScenarios,expectedAccesses,TTL,HORIZON} from './config.mjs';
import {correctness} from './correctness.mjs';

process.chdir(path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'));
const args=process.argv.slice(2),outIndex=args.indexOf('--out');
assert(outIndex>=0&&args[outIndex+1], 'Usage: node scripts/econ08/run.mjs --out results/local/econ08_run [--smoke]');
assert(args.every((x,i)=>x==='--out'||x==='--smoke'||i===outIndex+1),'Unknown argument');
const smoke=args.includes('--smoke'),out=path.resolve(args[outIndex+1]);
assert(!fs.existsSync(out)||fs.readdirSync(out).length===0,'Refusing to overwrite existing evidence; choose a new --out directory');
fs.mkdirSync(out,{recursive:true});
const env=prepare(),allScenarios=pilotScenarios();
const scenarios=smoke?allScenarios.filter(s=>s.id==='zk_B2_d86400_LOW'||s.id==='signed_control_d0_HIGH'):allScenarios;
const data={contexts:[],transactions:[],proofs:[],accesses:[],checks:[]},summaries=[];
const gitHead=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const sourceHashes=Object.fromEntries(sourceFiles.map(p=>[p,hash(fs.readFileSync(p))]));
const created=new Date().toISOString();
function summarize(s) {
  const txs=data.transactions.filter(t=>t.scenario===s.id),accesses=data.accesses.filter(a=>a.scenario===s.id);
  const sum=predicate=>txs.filter(predicate).reduce((n,t)=>n+Number(t.receipt.gasUsed),0);
  const userGas=sum(t=>['access','approval'].includes(t.category));
  const setupGas=sum(t=>['deployment','partition_setup'].includes(t.category)&&!t.excluded_from_system_cost);
  const initialPublicationGas=sum(t=>t.category==='initial_publication');
  const statusPublicationGas=sum(t=>t.category==='status_publication');
  summaries.push({scenario:s.id,mechanism:s.name,groups:s.groups,delta_seconds:s.delta,workload:s.workload,
    updates:s.updates.length,accesses:accesses.length,authorizations:accesses.filter(a=>a.event!=='hit').length,
    hits:accesses.filter(a=>a.event==='hit').length,
    holder_gas:userGas,operator_setup_gas:setupGas,issuer_initial_publication_gas:initialPublicationGas,
    issuer_status_publication_gas:statusPublicationGas,
    measured_boundary_gas:userGas+setupGas+initialPublicationGas+statusPublicationGas,
    excluded_fixture_gas:sum(t=>t.excluded_from_system_cost),
    potential_issuer_options:s.family==='zk'?4/s.groups:1,
    proof_count:accesses.filter(a=>a.proof_index!==null).length,
    calldata_bytes:txs.filter(t=>!t.excluded_from_system_cost).reduce((n,t)=>n+t.calldata_bytes,0)});
}
function csv(rows,cols) {return [cols.join(','),...rows.map(r=>cols.map(c=>JSON.stringify(r[c]??'')).join(','))].join('\n')+'\n';}
function save(status,error=null) {
  const report={schema_version:1,protocol:'ECON08_Technical_Protocol_v0_1',status,smoke,created_utc:created,
    updated_utc:new Date().toISOString(),git_head:gitHead,source_files_sha256:sourceHashes,
    environment:{node:process.version,platform:process.platform,arch:process.arch,cpu:os.cpus()[0]?.model,
      logical_cpus:os.cpus().length,solc:env.solc,settings:env.settings,hardfork:'osaka',chain_id:31337},setup:env.setup,
    design:{horizon_seconds:HORIZON,authorization_ttl_seconds:TTL,credential_expiry_seconds:HORIZON,
      root_presentation_grace_seconds:0,population:8,credentials_per_issuer:2,issuers:4,holder_issuer:0,
      holder_credential:0,update_order:'publication before access at equal timestamps',scenarios},
    contexts:data.contexts,summaries,checks:data.checks,
    counts:{workload_accesses:data.accesses.filter(a=>a.purpose==='workload').length,
      correctness_accesses:data.accesses.filter(a=>a.purpose==='correctness').length,
      rejected_transactions:data.transactions.filter(t=>t.category==='rejected').length,proofs:data.proofs.length},
    limits:[
      'Synthetic pilot on one local EVM and one machine; no public-network fee, throughput or population-scaling estimate.',
      'Native ZK B=1/2/4 and public signed diagnostic only. Bitstring Status List and PRC are not implemented or measured here.',
      'Signed control has different privacy. It retains the common four-issuer registry/publication boundary; not a minimal standalone signed deployment.',
      'System boundary includes all B registries/gates, shared Poseidon and ZK verifier once, partition setup, all four initial publications and both scheduled revocations, plus one observed holder. It is not a whole-population cost.',
      'Mock token deployment and one-unit gate bootstrap are recorded but excluded. One holder approval is included. Gate starts with a nonzero token balance.',
      'Issuance, witness delivery, hosting, communication and issuer-decision-to-publication latency are unmeasured, not zero.',
      'Delta starts at authoritative publication. Root presentation grace is zero. B=4 exposes issuer identity; group anonymity is conditional; wallet and scope nullifier link accesses.',
      'Inline proof timings are diagnostics, not independent timing replicates. Run timing.mjs in three fresh processes after the replay for timing evidence.',
      'Local phase-2 contributions are a demonstration setup, not a production trusted ceremony.',
    ],error};
  fs.writeFileSync(path.join(out,'report.json'),json(report));
  fs.writeFileSync(path.join(out,'accesses.json'),json(data.accesses));
  fs.writeFileSync(path.join(out,'receipts_and_proofs.json.gz'),gzipSync(json({transactions:data.transactions,proofs:data.proofs}),{level:9}));
  fs.writeFileSync(path.join(out,'verification_key.json'),json(env.vk));fs.copyFileSync('build/Verifier.sol',path.join(out,'Verifier.sol'));
  fs.writeFileSync(path.join(out,'summary.csv'),csv(summaries,Object.keys(summaries[0]??{scenario:null})));
  const ledger=data.transactions.map(t=>({scenario:t.scenario,purpose:t.purpose,category:t.category,actor:t.actor,
    timestamp:t.timestamp,gas:Number(t.receipt.gasUsed),calldata_bytes:t.calldata_bytes,tx_hash:t.receipt.hash,
    status:t.receipt.status,excluded_from_system_cost:!!t.excluded_from_system_cost}));
  fs.writeFileSync(path.join(out,'cost_ledger.csv'),csv(ledger,Object.keys(ledger[0]??{scenario:null})));
  const names=['report.json','accesses.json','receipts_and_proofs.json.gz','verification_key.json','Verifier.sol','summary.csv','cost_ledger.csv'];
  fs.writeFileSync(path.join(out,'manifest.json'),json(Object.fromEntries(names.map(n=>[n,hash(fs.readFileSync(path.join(out,n)))]))));
}
try {
  for(const s of scenarios) {
    const c=await context(env,data,s),expected=expectedAccesses(s);
    try {
      // Do not drop day-31/day-63 publications merely because LOW last accesses on day 0.
      const events=[...s.updates.map(u=>({...u,kind:'update'})),...expected.map((a,i)=>({...a,index:i,kind:'access'}))]
        .sort((a,b)=>a.at-b.at||(a.kind===b.kind?0:a.kind==='update'?-1:1));
      for(const e of events) if(e.kind==='update') await c.revoke(e.issuer,e.credential,c.base+BigInt(e.at));
        else await c.deposit(c.base+BigInt(e.at),{index:e.index,expectedEvent:e.event});
      c.check('workload_complete',{accesses:s.accesses.length,updates:s.updates.length});
      summarize(s);
    } finally {await c.connection.close();}
    save('RUNNING');console.log(`PASS ${s.id}: authorizations=${summaries.at(-1).authorizations}`);
  }
  if(!smoke)await correctness(env,data,()=>save('RUNNING'));
  save(smoke?'SMOKE_PASS':'PASS');console.log(json({status:smoke?'SMOKE_PASS':'PASS',scenarios:summaries.length,checks:data.checks.length,proofs:data.proofs.length}));
} catch(e) {save('FAIL',{message:e.message,stack:e.stack});throw e;}
process.exit(0);
