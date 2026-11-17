#!/usr/bin/env python3
"""Independent reconstruction of saved seed-level summary statistics."""
import gzip
import json
import math
from pathlib import Path
import statistics
from scipy.stats import t

root=Path(__file__).parents[1]/'results'


def read(path):
    if path.exists():return path.read_text()
    return gzip.decompress(Path(str(path)+'.gz').read_bytes()).decode()


def compare(records,summary):
    for row in summary:
        sample=[r for r in records if r['case']==row['case']]
        assert len(sample)==20 and sorted(r['seed'] for r in sample)==list(range(20))
        for key in ('accuracy','posterior_entropy_bits','identified_fraction','first_confident_wrong_fraction','full_per_holder'):
            values=[r[key] for r in sample]
            assert math.isclose(statistics.mean(values),row[key],rel_tol=1e-12,abs_tol=1e-12),(row['case'],key)
            half=t.ppf(.975,19)*statistics.stdev(values)/math.sqrt(20)
            assert math.isclose(half,row[key+'_ci95_halfwidth'],rel_tol=1e-10,abs_tol=1e-12),(row['case'],key,'CI')


if __name__=='__main__':
    stress=[json.loads(line) for line in read(root/'stress/runs.jsonl').splitlines()]
    summary=json.loads(read(root/'stress/summary.json'));assert len(stress)==1600 and len(summary)==80;compare(stress,summary)
    ofat=[r for file in sorted((root/'ofat1000').glob('case_*.json')) for r in json.loads(file.read_text())]
    os=json.loads(read(root/'ofat1000/summary.json'));assert len(ofat)==300 and len(os)==15;compare(ofat,os)
    calibrated=json.loads(read(root/'calibrated/runs.json'));cs=json.loads(read(root/'calibrated/summary.json'));assert len(calibrated)==60
    for row in cs:
        sample=[r for r in calibrated if r['issuers']==row['issuers']];assert len(sample)==20
        assert math.isclose(statistics.mean(r['accuracy'] for r in sample),row['accuracy'],rel_tol=1e-12)
    gate=json.loads(read(root/'data_gate.json'));assert gate['gate']=='INDEXER_INSUFFICIENT' and gate['chain_validated_gate']=='UNKNOWN'
    for source in gate['reports']:
        assert source['aggregate_matches_pagination'] and source['aggregate_revocation_count']==source['onchain_revocations_returned']
        assert sum(c['revocations'] for c in source['candidates'])==source['onchain_revocations_returned']
    result=dict(status='PASS',stress_runs=1600,ofat_runs=300,calibrated_runs=60,
                total_seed_runs=1960,confidence_interval_method='Student t on 20 independent seed means',
                data_gate='Indexer-insufficient; no independent full chain coverage asserted')
    (root/'numerical_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
