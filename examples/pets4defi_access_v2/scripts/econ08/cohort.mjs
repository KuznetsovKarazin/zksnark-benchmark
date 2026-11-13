import assert from 'node:assert/strict';
import {DAY, HORIZON, TTL, WORKLOADS} from './config.mjs';
import {hash} from './harness.mjs';

export const POPULATIONS = [16, 128, 512];
export const COHORT_ISSUERS = [0, 1, 2, 3];
export const SEED = 'ECON08-cohort-v1';

export function cohortFixture(population) {
  assert(POPULATIONS.includes(population));
  const perIssuer = population / COHORT_ISSUERS.length;
  return {population, perIssuer, populate(fixture) {
    for (const issuer of COHORT_ISSUERS) {
      const credentials = fixture.credentials[issuer];
      for (let index = 0; index < perIssuer; index++) {
        const original = credentials[index % 2];
        const value = name => BigInt(`0x${hash(`${SEED}/${issuer}/${index}/${name}`).slice(0, 48)}`);
        const credential = {...original, secret: value('secret'), salt: value('salt')};
        if (index < 2) credentials[index] = credential;
        else credentials.push(credential);
      }
      fixture.setCredential(issuer, 0, {});
    }
  }};
}

export const WEEKLY_UPDATES = Array.from({length: 12}, (_, i) => ({
  at: (i + 1) * 7 * DAY,
  issuer: i % 4,
  credential: 1 + Math.floor(i / 4),
}));

// One holder per issuer, all using credential 0. At shared timestamps an update
// precedes all accesses. Visit holders in issuer order to make receipts auditable.
export function cohortEvents(scenario) {
  const events = scenario.updates.map(update => ({...update, type: 'update'}));
  for (const issuer of COHORT_ISSUERS) {
    const group = Math.floor(issuer / (4 / scenario.groups));
    let last = null;
    for (const [index, at] of WORKLOADS[scenario.workload].entries()) {
      const invalidation = scenario.family === 'zk' && last !== null && scenario.updates.find(update =>
        update.at > last && update.at <= at && Math.floor(update.issuer / (4 / scenario.groups)) === group);
      const stale = invalidation && at >= invalidation.at + scenario.delta;
      const event = last === null ? 'first' : at >= Math.min(last + TTL, HORIZON) || stale ? 'reauthorize' : 'hit';
      if (event !== 'hit') last = at;
      events.push({at, issuer, index, event, type: 'access'});
    }
  }
  return events.sort((a, b) => a.at - b.at || Number(a.type === 'access') - Number(b.type === 'access') || a.issuer - b.issuer);
}
