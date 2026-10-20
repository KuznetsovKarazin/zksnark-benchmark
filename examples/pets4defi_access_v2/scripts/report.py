#!/usr/bin/env python3
"""Render a concise results note from raw evidence, without third-party packages."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT/'results'/name).read_text())
def number(value):
    return f'{float(value):,.1f}'
def main():
    m=read('measurements.json'); tests=read('test_results.json')
    rows=list(csv.DictReader((ROOT/'results/event_measurements.csv').open()))
    index={(r['chain'],r['variant'],r['event'],r['metric']):r for r in rows}
    lines=['# Measured results: PETs4DeFi v2','',
        f"Recorded: {m['metadata']['recorded_at']}. Source revision: `{m['metadata']['source_sha']}`.",
        f"Exact measured source-file hashes: `results/measurements.json`. Debug run: **{m['metadata']['debug_run']}**.",
        '',f"Integration/assertion checks: **{tests['passed']} passed, {tests['failed']} failed** across the two runtimes.",
        'These counts include assertions, negative cases and state invariants; they are not independent security audits.',
        '', '## Receipt gas', '',
        'Medians; brackets show IQR. First-holder registration/access is one observation; recurring rows have 30 observations in the main run.',
        '', '| Chain / treatment | First access or registration | Recurring direct access / cache hit | Cache reauthorization |',
        '|---|---:|---:|---:|']
    for chain in ['l1','op']:
        for variant in m['metadata']['variants']:
            cache=variant.endswith('_cache')
            def value(event):
                r=index[(chain,variant,event,'gas_used')]
                return f"{number(r['median'])} [{number(r['iqr'])}]; n={r['n']}"
            lines.append(f"| {chain} / {variant} | {value('cache_register_first' if cache else 'access_first')} | {value('cache_hit' if cache else 'access_repeat')} | {value('cache_reauthorize') if cache else '—'} |")
    lines+=['','Both chains are local simulations. OP rows exclude L1 data and operator fees. Gas equality does not imply equal transaction prices.',
        '', '## Effect of status updates', '',
        'Example projection: 100 total accesses, one app, 1,000 users, 90-day credential, 30-day cache TTL, 90-day horizon. Includes separately recorded demo setup and registry costs allocated over users. This is a trace calculation, not a population benchmark.',
        '', '| Root-change workload | Treatment | Full authorizations | Cache hits | Known execution gas / user |','|---|---|---:|---:|---:|']
    for r in csv.DictReader((ROOT/'results/architecture_results.csv').open()):
        if r['chain']=='l1' and r['n_accesses']=='100' and r['apps_deployed']=='1' and r['population']=='1000' and r['validity_days']=='90':
            lines.append(f"| {r['root_churn']} | {r['variant']} | {r['full_authorizations_per_user']} | {r['cache_hits_per_user']} | {number(r['known_execution_gas_per_user'])} |")
    lines+=['','This common-registry comparison charges the shared root workload to both families. It is not a minimal signed-only deployment cost. Unknown service, witness distribution and user costs are not set to zero.','', '## Server prover evidence','']
    path=ROOT/'results/server_prover.json'
    if path.exists():
        p=read('server_prover.json')
        lines+=[f"{p['cpu']}; {p['node']}; {p['mode']}.",'','| Measurement | n | Median ms | IQR ms |','|---|---:|---:|---:|']
        for name,s in p['summary'].items():lines.append(f"| {name} | {s['n']} | {number(s['median'])} | {number(s['iqr'])} |")
        lines+=['',p['cold_definition'],p['proof_timer']]
    else:lines+=['Separate 30-run cold/warm server report has not been generated in this checkout.']
    lines+=['','**Browser and physical phone: unmeasured.** The executable harness is provided; server numbers must not be relabelled as mobile performance.',
        '', '## Evidence and interpretation', '',
        '- `measurements.json`: environment, setup provenance, exact source hashes and successful gas events.',
        '- `transactions.json`, `proof_samples.json`, `test_results.json`: raw receipts, verified proof timings and checks.',
        '- `fee_snapshot.json` / `fee_history_raw.json.gz`: timestamped public fee evidence and raw RPC archive.',
        '- `architecture_results.csv`, `trace_counts.csv`, `trace_events.csv`, `break_even.csv`: inspectable state-trace accounting.',
        '- `price_inputs.csv`: missing prices and fee components; assumed stresses and observed fee conversions are distinct.',
        '', 'Read THREAT_MODEL.md and REVIEW_RESPONSE.md before using these numbers in an article. The result is a reproducible architecture experiment with limited privacy properties, not a production system or completed empirical cost–privacy frontier.', '']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines))
    print(ROOT/'RESULTS.md')
if __name__=='__main__':main()
