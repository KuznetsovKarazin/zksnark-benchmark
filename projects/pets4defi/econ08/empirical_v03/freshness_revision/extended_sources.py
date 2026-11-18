"""Independent 180-day EAS registry screen with aggregate output."""
import argparse
import concurrent.futures
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/"src"))
import indexer_gate

START="2026-05-21T00:00:00Z"
END="2026-11-17T00:00:00Z"
indexer_gate.ENDPOINTS.update(arbitrum="https://arbitrum.easscan.org/graphql",linea="https://linea.easscan.org/graphql",scroll="https://scroll.easscan.org/graphql")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--private-dir",required=True,type=Path)
    args=parser.parse_args()
    spec=json.loads((ROOT.parent/"config/protocol.json").read_text())
    spec.update(window_start=START,window_end_exclusive=END)
    def one(name):
        try:
            report=indexer_gate.audit(name,args.private_dir,spec)
            return report if isinstance(report,dict) else json.loads((args.private_dir/name/"report.json").read_text())
        except Exception as e:
            return dict(chain=name,errors=[str(e)],indexer_pagination_complete=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs={pool.submit(one,n):n for n in indexer_gate.ENDPOINTS}
        for job in concurrent.futures.as_completed(jobs):
            report=job.result()
            key=jobs[job]
            report["watermark_note"]="Last indexed issuance is an activity date, not an index-completeness watermark."
            if not report.get("indexer_pagination_complete"):
                report["returned_in_partial_pages"]=report.get("onchain_revocations_returned")
                report["onchain_revocations_returned"]=None
            (ROOT/"results"/f"eas180_{key}.json").write_text(json.dumps(report,indent=2)+"\n")
            print(key,report.get("onchain_revocations_returned"),report.get("indexer_pagination_complete"),report.get("errors"),flush=True)


if __name__=="__main__":
    main()
