import test from 'node:test';
import assert from 'node:assert/strict';
import {DAY, TTL, HORIZON, pilotScenarios, expectedAccesses} from './config.mjs';

test('complete, unique pilot matrix and exact integer schedules', () => {
  const scenarios = pilotScenarios();
  assert.equal(scenarios.length, 32);
  assert.equal(new Set(scenarios.map(s => s.id)).size, 32);
  assert.equal(scenarios.reduce((n, s) => n + s.accesses.length, 0), 1616);
  for (const s of scenarios) {
    assert(s.accesses.every(Number.isSafeInteger));
    assert(s.accesses.every(t => t >= 0 && t < HORIZON));
    assert.equal(s.updates.length, s.id.endsWith('no_updates') ? 0 : 2);
  }
});
test('exclusive deadlines, exact TTL, and update before simultaneous access', () => {
  const s = {family: 'zk', groups: 1, delta: 3600,
    updates: [{at: DAY, issuer: 3}], accesses: [0, DAY, DAY + 3599, DAY + 3600, DAY + 3601]};
  assert.deepEqual(expectedAccesses(s).map(r => r.event), ['first','hit','hit','reauthorize','hit']);
  assert.deepEqual(expectedAccesses({...s, delta: 0}).map(r => r.event), ['first','reauthorize','hit','hit','hit']);
  assert.deepEqual(expectedAccesses({...s, updates: [], accesses: [0, TTL - 1, TTL]}).map(r => r.event), ['first','hit','reauthorize']);
});
test('second invalidation does not postpone the old context deadline', () => {
  const s = {family:'zk', groups:1, delta:DAY,
    updates:[{at:DAY,issuer:3},{at:DAY+1,issuer:1}], accesses:[0,2*DAY-1,2*DAY]};
  assert.deepEqual(expectedAccesses(s).map(r=>r.event), ['first','hit','reauthorize']);
});
test('independent control and isolated group do not invalidate unrelated holders', () => {
  for (const family of ['zk','signed']) {
    const s={family,groups:4,delta:0,updates:[{at:DAY,issuer:3}],accesses:[0,DAY,TTL]};
    assert.deepEqual(expectedAccesses(s).map(r=>r.event), ['first','hit','reauthorize']);
  }
});
test('hand-calculated authorization counts for HIGH', () => {
  const expected={zk_B1:[5,5,4],zk_B2:[4,4,4],zk_B4:[3,3,3],signed_control:[3,3,3]};
  for (const [name, counts] of Object.entries(expected)) {
    const actual=pilotScenarios().filter(s=>s.name===name&&s.workload==='HIGH'&&s.updates.length)
      .map(s=>expectedAccesses(s).filter(e=>e.event!=='hit').length);
    assert.deepEqual(actual, counts, name);
  }
});
