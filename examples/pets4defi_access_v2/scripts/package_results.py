#!/usr/bin/env python3
"""Package generated CSVs byte-for-byte in a deterministic, inspectable bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

def package(directory):
    files=sorted(directory.glob('*.csv'))
    if not files: raise ValueError('No CSVs to package')
    rows=[]
    target=directory/'economic_tables.zip'
    temporary=target.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in files:
            if path.is_symlink() or not path.is_file(): raise ValueError('Expected ordinary CSV file')
            data=path.read_bytes()
            entry=zipfile.ZipInfo(path.name,date_time=(1980,1,1,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED
            entry.create_system=3
            entry.external_attr=0o100644<<16
            archive.writestr(entry,data,compresslevel=9)
            rows.append({'name':path.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None: raise ValueError('ZIP CRC failure')
        for row in rows:
            assert hashlib.sha256(archive.read(row['name'])).hexdigest()==row['sha256']
    temporary.replace(target)
    manifest={'archive':target.name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
              'bytes':target.stat().st_size,'source_bytes':sum(r['bytes'] for r in rows),'files':rows}
    (directory/'economic_tables_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir',type=Path,default=Path(__file__).resolve().parents[1]/'results')
    args=parser.parse_args()
    result=package(args.results_dir)
    print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
