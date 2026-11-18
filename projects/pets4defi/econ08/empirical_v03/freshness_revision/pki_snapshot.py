"""Catalogue and cryptographically check one disclosed full-CRL endpoint per CA owner."""
import argparse
import concurrent.futures
import csv
import datetime as dt
import hashlib
import io
import json
from collections import Counter,defaultdict
from pathlib import Path
import urllib.parse
import urllib.request
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtensionOID

ROOT=Path(__file__).resolve().parent
BASE="https://ccadb.my.salesforce-sites.com/ccadb/"
START=dt.date(2026,5,21)
END=dt.date(2026,11,17)


def download(url,limit):
    req=urllib.request.Request(url,headers={"User-Agent":"ECON08-academic-CRL-snapshot/1"})
    with urllib.request.urlopen(req,timeout=12) as r:
        data=r.read(limit+1)
    if len(data)>limit:
        raise ValueError("Source exceeds study size cap")
    return data


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--cache",required=True,type=Path)
    args=parser.parse_args()
    args.cache.mkdir(exist_ok=True,parents=True)
    catalogue=args.cache/"ccadb_v5.csv"
    if not catalogue.exists():
        catalogue.write_bytes(download(BASE+"AllCertificateRecordsCSVFormatV5",40_000_000))
    with catalogue.open(encoding="utf-8-sig") as f:
        all_rows=list(csv.DictReader(f))
    by_owner=defaultdict(list)
    for r in all_rows:
        if (r["Certificate Record Type"]!="Intermediate Certificate" or r["Mozilla Status"]!="Trusted"
            or r["TLS Capable"]!="True" or r["Revocation Status"]!="Not Revoked"):
            continue
        if not r["Valid From (GMT)"] <= "2026.11.17" <= r["Valid To (GMT)"]:
            continue
        urls=json.loads(r["JSON Array of All Full CRL URLs"] or "[]")
        if urls:
            # Use catalogue-reported accountable owner. Possible delegation is recorded.
            by_owner[r["CA Owner"]].append((r,sorted(urls)[0]))
    # One deterministic key/endpoint per declared owner; no selection by outcome.
    sample=[min(rows,key=lambda x:(x[0]["SHA-256 Fingerprint"],x[1])) for rows in by_owner.values()]
    years=sorted({r["Valid From (GMT)"][:4] for r,_ in sample})
    def certificates(year):
        f=args.cache/("pems_"+year+".csv")
        if not f.exists():
            f.write_bytes(download(BASE+"AllCertificatePEMsCSVFormat?NotBeforeYear="+year,30_000_000))
        with f.open(encoding="utf-8-sig") as s:
            return {r["SHA-256 Fingerprint"]:r["X.509 Certificate (PEM)"] for r in csv.DictReader(s)}
    pems={};pem_errors={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for year,job in [(y,ex.submit(certificates,y)) for y in years]:
            try:pems.update(job.result())
            except Exception as e:pem_errors[year]=str(e)[:140]
    def inspect(item):
        r,url=item;fp=r["SHA-256 Fingerprint"]
        row={"owner":r["CA Owner"],"subordinate_owner":r["Subordinate CA Owner"],"cert_sha256":fp,
             "source_url":url,"status":"unavailable"}
        counts=Counter()
        try:
            cert=x509.load_pem_x509_certificate(pems[fp].encode())
            if cert.fingerprint(hashes.SHA256()).hex().upper()!=fp:
                raise ValueError("CA certificate fingerprint mismatch")
            # Prefer HTTPS transport on the same declared host/path. The CA signature is checked independently.
            parts=urllib.parse.urlsplit(url)
            if parts.scheme not in ("https","http"):raise ValueError("Non-HTTP distribution point")
            preferred=urllib.parse.urlunsplit(("https",parts.netloc,parts.path,parts.query,""))
            cache=args.cache/(fp+".crl")
            if not cache.exists():
                try:blob=download(preferred,16_000_000);row["retrieved_url"]=preferred
                except Exception:
                    if url==preferred:raise
                    blob=download(url,16_000_000);row["retrieved_url"]=url
                cache.write_bytes(blob)
            blob=cache.read_bytes()
            crl=x509.load_pem_x509_crl(blob) if b"-----BEGIN" in blob[:80] else x509.load_der_x509_crl(blob)
            if crl.issuer!=cert.subject or not crl.is_signature_valid(cert.public_key()):
                raise ValueError("Signer or signature mismatch")
            if any(x.oid==ExtensionOID.DELTA_CRL_INDICATOR for x in crl.extensions):
                raise ValueError("Delta CRL")
            for ext in crl.extensions:
                if ext.oid==ExtensionOID.ISSUING_DISTRIBUTION_POINT and (ext.value.indirect_crl or ext.value.only_contains_ca_certs):
                    raise ValueError("Indirect or CA-only CRL")
            row.update(sha256=hashlib.sha256(blob).hexdigest(),this_update=crl.last_update_utc.isoformat(),
                       next_update=crl.next_update_utc.isoformat() if crl.next_update_utc else None,
                       entries_in_snapshot=len(crl))
            if crl.last_update_utc.date()>END:
                raise ValueError("Snapshot after study date")
            for rev in crl:
                day=rev.revocation_date_utc.date()
                if START<=day<END: counts[str(day)]+=1
            row.update(status="signed_stock_only",retained_window_entries=sum(counts.values()),active_retained_dates=len(counts))
        except Exception as e:row["reason"]=str(e)[:170]
        return row,counts
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        checked=list(ex.map(inspect,sample))
    study={"source":BASE+"AllCertificateRecordsCSVFormatV5","catalogue_sha256":hashlib.sha256(catalogue.read_bytes()).hexdigest(),
           "catalogue_rows":len(all_rows),"candidate_certificate_records_with_full_urls":sum(map(len,by_owner.values())),
           "owner_clusters_sampled":len(sample),"verified_full_crl_snapshots":sum(r["status"]=="signed_stock_only" for r,_ in checked),
           "collection_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"pem_fetch_errors":pem_errors,
           "coverage":"One selected endpoint and one current stock per CA owner. Historical publication flows are unverified.",
           "records":[r for r,_ in checked]}
    (ROOT/"results/web_pki_inventory.json").write_text(json.dumps(study,indent=2,sort_keys=True)+"\n")
    with (ROOT/"results/web_pki_retained_dates.csv").open("w") as f:
        w=csv.writer(f);w.writerow(["owner","cert_sha256","effective_revocation_date","entries_retained_in_snapshot"])
        for row,counts in checked:
            if row["status"]=="signed_stock_only":
                for day,n in sorted(counts.items()):w.writerow([row["owner"],row["cert_sha256"],day,n])
    print(study["owner_clusters_sampled"],study["verified_full_crl_snapshots"])


if __name__=="__main__":
    main()
