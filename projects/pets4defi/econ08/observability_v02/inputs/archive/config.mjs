// ECON-08 v0.1 native pilot. Times are integer seconds, never rounded days.
export const DAY = 86400;
export const HORIZON = 90 * DAY;
export const TTL = 30 * DAY;
export const DELTAS = [0, 3600, DAY];
export const MECHANISMS = [
  {name: 'zk_B1', family: 'zk', groups: 1},
  {name: 'zk_B2', family: 'zk', groups: 2},
  {name: 'zk_B4', family: 'zk', groups: 4},
  {name: 'signed_control', family: 'signed', groups: 1},
];
export const UPDATES = [
  {at: 31 * DAY, issuer: 3, credential: 1},
  {at: 63 * DAY, issuer: 1, credential: 1},
];
export const WORKLOADS = {
  LOW: [0],
  HIGH: Array.from({length: 100}, (_, i) => Math.floor(i * HORIZON / 100)),
};
export function pilotScenarios() {
  const scenarios = [];
  for (const mechanism of MECHANISMS) {
    for (const delta of DELTAS) for (const [workload, accesses] of Object.entries(WORKLOADS)) {
      scenarios.push({...mechanism, delta, workload, accesses, updates: UPDATES,
        id: `${mechanism.name}_d${delta}_${workload}`});
    }
    for (const [workload, accesses] of Object.entries(WORKLOADS)) {
      scenarios.push({...mechanism, delta: 0, workload, accesses, updates: [],
        id: `${mechanism.name}_d0_${workload}_no_updates`});
    }
  }
  return scenarios;
}

// Specification-level oracle. No contract calls, observed cache decisions or gas.
export function expectedAccesses(scenario) {
  let lastAuthorization = null;
  let expires = -1;
  return scenario.accesses.map(at => {
    const firstInvalidation = scenario.family === 'zk' && lastAuthorization !== null
      ? scenario.updates.find(e => e.at > lastAuthorization && e.at <= at
        && Math.floor(e.issuer / (4 / scenario.groups)) === 0)
      : undefined;
    const stale = firstInvalidation !== undefined && at >= firstInvalidation.at + scenario.delta;
    const event = lastAuthorization === null ? 'first'
      : (at >= expires || stale ? 'reauthorize' : 'hit');
    if (event !== 'hit') {
      lastAuthorization = at;
      expires = Math.min(at + TTL, HORIZON);
    }
    return {at, event};
  });
}
