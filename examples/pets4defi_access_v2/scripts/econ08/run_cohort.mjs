import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseArgs} from 'node:util';
import {gzipSync} from 'node:zlib';
import {DELTAS, HORIZON, MECHANISMS, TTL, WORKLOADS} from './config.mjs';
import {COHORT_ISSUERS, SEED, WEEKLY_UPDATES, cohortEvents, cohortFixture} from './cohort.mjs';
import {context, hash, json, prepare, sourceFiles} from './harness.mjs';

process.chdir(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..'));
const {values: options} = parseArgs({options: {
  out: {type: 'string'}, population: {type: 'string'}, mechanism: {type: 'string'},
  delta: {type: 'string', default: '0'}, workload: {type: 'string', default: 'HIGH'},
  'no-updates': {type: 'boolean'},
}});
assert(options.out, 'Use --out DIR --population 16|128|512 --mechanism zk_B1|zk_B2|zk_B4|signed_control');
const cohort = cohortFixture(Number(options.population));
const mechanism = MECHANISMS.find(item => item.name === options.mechanism);
assert(mechanism, 'Unknown mechanism');
const delta = Number(options.delta), workload = options.workload;
assert(DELTAS.includes(delta) && Object.hasOwn(WORKLOADS, workload));
const id = `N${cohort.population}_${mechanism.name}_d${delta}_${workload}_${options['no-updates'] ? 'control' : 'weekly'}`;
const scenario = {...mechanism, id, delta, workload, updates: options['no-updates'] ? [] : WEEKLY_UPDATES};
const out = path.resolve(options.out);
fs.mkdirSync(path.dirname(out), {recursive: true});
fs.mkdirSync(out);

const data = {contexts: [], transactions: [], proofs: [], accesses: [], checks: []};
const report = {
  protocol: 'ECON08_Technical_Protocol_v0_1', stage: 'balanced_cohort', status: 'RUNNING',
  git_head: execFileSync('git', ['rev-parse', 'HEAD'], {encoding: 'utf8'}).trim(),
  created_utc: new Date().toISOString(), seed: SEED, scenario,
  design: {population: cohort.population, per_issuer: cohort.perIssuer, registry_capacity_per_issuer: 1024,
    observed_holders: COHORT_ISSUERS.length, measured_credential_index: 0, ttl_seconds: TTL,
    horizon_seconds: HORIZON, root_presentation_grace_seconds: 0, access_offsets_seconds: WORKLOADS[workload]},
  source_files_sha256: Object.fromEntries([...sourceFiles, 'scripts/econ08/cohort.mjs', 'scripts/econ08/run_cohort.mjs']
    .map(file => [file, hash(fs.readFileSync(file))])),
};
fs.writeFileSync(path.join(out, 'report.json'), json(report));
let env;
try {
  env = prepare();
  report.environment = {node: process.version, platform: process.platform, arch: process.arch,
    cpu: os.cpus()[0]?.model, solc: env.solc, settings: env.settings, hardfork: 'osaka', chain_id: 31337};
  report.setup = env.setup;
  const chain = await context(env, data, {...scenario, cohort});
  try {
    for (const event of cohortEvents(scenario)) {
      const time = chain.base + BigInt(event.at);
      if (event.type === 'update') await chain.revoke(event.issuer, event.credential, time);
      else await chain.deposit(time, {issuer: event.issuer, index: event.index, expectedEvent: event.event});
    }
  } finally {
    await chain.connection.close();
  }
  const gas = rows => rows.reduce((sum, tx) => sum + Number(tx.receipt.gasUsed), 0);
  const txByCategory = category => data.transactions.filter(tx => tx.category === category && !tx.excluded_from_system_cost);
  report.context = data.contexts[0];
  report.checks = data.checks;
  report.holders = COHORT_ISSUERS.map(issuer => {
    const actor = `holder_${issuer}`, rows = data.accesses.filter(row => row.holder_issuer === issuer);
    assert.equal(rows.length, WORKLOADS[workload].length);
    return {issuer, accesses: rows.length, authorizations: rows.filter(row => row.event !== 'hit').length,
      gas: gas(data.transactions.filter(tx => tx.actor === actor && ['approval', 'access'].includes(tx.category)))};
  });
  report.gas = {holder_cohort: report.holders.reduce((sum, row) => sum + row.gas, 0),
    operator_setup: gas([...txByCategory('deployment'), ...txByCategory('partition_setup')]),
    initial_publication: gas(txByCategory('initial_publication')), status_publication: gas(txByCategory('status_publication')),
    excluded_fixture: gas(data.transactions.filter(tx => tx.excluded_from_system_cost))};
  report.status = 'PASS';
  console.log(id, report.holders.map(row => row.authorizations), report.gas);
} catch (error) {
  report.status = 'FAIL';
  report.error = error.stack;
  process.exitCode = 1;
  console.error(error);
} finally {
  fs.writeFileSync(path.join(out, 'report.json'), json(report));
  fs.writeFileSync(path.join(out, 'accesses.json'), json(data.accesses));
  fs.writeFileSync(path.join(out, 'receipts_and_proofs.json.gz'), gzipSync(json({transactions: data.transactions, proofs: data.proofs})));
  const names = ['report.json', 'accesses.json', 'receipts_and_proofs.json.gz'];
  if (env) {
    fs.writeFileSync(path.join(out, 'verification_key.json'), json(env.vk));
    names.push('verification_key.json');
  }
  fs.writeFileSync(path.join(out, 'manifest.json'), json(Object.fromEntries(names.map(name =>
    [name, hash(fs.readFileSync(path.join(out, name)))]))));
}
process.exit(process.exitCode ?? 0);
