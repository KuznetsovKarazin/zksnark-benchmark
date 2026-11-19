#!/usr/bin/env python3
"""Extract assigned-actor actual-gas debits from eight archived ECON08 runs."""
from pathlib import Path
import argparse,gzip,hashlib,json

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',type=Path,required=True)
    ap.add_argument('--out',type=Path,default=Path(__file__).with_name('trace_inputs.json'))
    a=ap.parse_args();root=a.repo/'examples/pets4defi_access_v2/results/econ08_cohort/runs'
    runs=[]
    for mech in ['zk_B1','zk_B2','zk_B4','signed_control']:
        for schedule in ['weekly','control']:
            name=f'N16_{mech}_d0_HIGH_{schedule}';p=root/name
            report=json.loads((p/'report.json').read_text())
            accesses=json.loads((p/'accesses.json').read_text())
            manifest=json.loads((p/'manifest.json').read_text())
            provenance={}
            for f in ['report.json','accesses.json','receipts_and_proofs.json.gz']:
                sha=hashlib.sha256((p/f).read_bytes()).hexdigest()
                assert sha==manifest[f];provenance[f]=sha
            txs=json.load(gzip.open(p/'receipts_and_proofs.json.gz','rt'))['transactions']
            lookup={x['tx_hash']:x for x in accesses};assert len(lookup)==400
            events=[];origin=report['context']['base']-3600
            for seq,tx in enumerate(txs):
                if tx['purpose']!='workload':continue
                cat=tx['category']
                if cat.startswith('fixture_') or (cat=='deployment' and tx.get('component')=='MockToken'):continue
                assert cat in ['deployment','partition_setup','approval','access','initial_publication','status_publication']
                rc=tx['receipt'];assert rc['status']==1
                mode=''
                if cat=='access':
                    ac=lookup[rc['hash']];assert int(rc['gasUsed'])==ac['gas']
                    assert tx['timestamp']==report['context']['base']+ac['at']
                    mode=ac['event']
                events.append({'t':tx['timestamp']-origin,'seq':seq,'actor':tx['actor'],
                    'category':cat,'access_event':mode,'gas':int(rc['gasUsed'])})
            events.sort(key=lambda x:(x['t'],x['seq']))
            holder=sum(x['gas'] for x in events if x['actor'].startswith('holder_'))
            assert holder==report['gas']['holder_cohort']
            assert sum(x['gas'] for x in events)==sum(report['gas'][k] for k in ['holder_cohort','operator_setup','initial_publication','status_publication'])
            assert sum(x['category']=='approval' for x in events)==4
            runs.append({'scenario':name,'mechanism':mech,'schedule':schedule,'N_issued':16,'A_active':4,
                'origin_epoch':origin,'access_base_offset':3600,'horizon_seconds':3600+report['design']['horizon_seconds'],
                'source_git_head':report['git_head'],'source_hashes':provenance,'events':events})
    a.out.write_text(json.dumps({'kind':'archived_actual_gas_debits_assigned_to_semantic_actors','runs':runs},separators=(',',':'))+'\n')
    print(json.dumps({'runs':len(runs),'events':sum(len(x['events']) for x in runs),'bytes':a.out.stat().st_size,'sha256':hashlib.sha256(a.out.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
