"""Normalize fully acquired public logs into private replay inputs.

Actual wallet addresses and per-wallet paths must not be committed. This module
does not link EAS recipients to DeFi users. Assignments in replay are randomized.
"""
import collections
import gzip
import hashlib
import json
from pathlib import Path
from acquire import (load_logs,timestamp,SUPPLY_AAVE,WITHDRAW_AAVE,SUPPLY_COMET,WITHDRAW_COMET,REVOKED)


def address(topic):
    if not isinstance(topic,str) or len(topic)!=66 or any(c!='0' for c in topic[2:26]):
        raise ValueError('Malformed indexed address')
    return '0x'+topic[-40:].lower()


def decode(row,source):
    topics=row['topics'];kind=topics[0].lower()
    if source.startswith('eas_'):
        if kind!=REVOKED or len(topics)!=4 or len(row['data'])!=66:raise ValueError('Malformed EAS Revoked event')
        return dict(kind='revocation',attester=address(topics[2]),schema=topics[3],uid=row['data'])
    if source=='aave_base':
        if len(topics)!=4:raise ValueError('Malformed Aave event')
        if kind==SUPPLY_AAVE:
            if len(row['data'])!=130:raise ValueError('Malformed Aave Supply data')
            return dict(kind='supply',beneficiary=address(topics[2]),initiator=address('0x'+row['data'][2:66]),asset=address(topics[1]))
        if kind==WITHDRAW_AAVE:
            if len(row['data'])!=66:raise ValueError('Malformed Aave Withdraw data')
            return dict(kind='withdraw',beneficiary=address(topics[2]),recipient=address(topics[3]),asset=address(topics[1]))
    if source=='compound_base':
        if len(topics)!=3 or len(row['data'])!=66:raise ValueError('Malformed Comet event')
        if kind==SUPPLY_COMET:return dict(kind='supply',beneficiary=address(topics[2]),initiator=address(topics[1]))
        if kind==WITHDRAW_COMET:return dict(kind='withdraw',beneficiary=address(topics[1]),recipient=address(topics[2]))
    raise ValueError('Unknown source/topic')


def normalize(folder):
    folder=Path(folder);manifest,raw=load_logs(folder)
    file=folder/'enriched_logs.json.gz';data=file.read_bytes()
    if hashlib.sha256(data).hexdigest()!=manifest.get('enriched',{}).get('sha256'):raise ValueError('Missing or corrupt timestamp enrichment')
    records=json.loads(gzip.decompress(data))
    if len(records)!=len(raw):raise ValueError('Enrichment count mismatch')
    source=manifest['source'];start=timestamp(manifest['start']);end=timestamp(manifest['end_exclusive'])
    paths=collections.defaultdict(list);revocations=collections.defaultdict(list)
    tx_seen=set();duplicates=0
    for row in records:
        event=decode(row,source);at=row['timestamp']-start
        if not 0<=at<end-start:raise ValueError('Event outside requested window')
        if event['kind']=='revocation':
            revocations[event['attester']].append(at)
        else:
            # One address/transaction interaction, not one transfer/log. Multi-
            # event operations should not inflate the apparent access frequency.
            key=(event['beneficiary'],row['transactionHash'])
            if key in tx_seen:duplicates+=1;continue
            tx_seen.add(key);paths[event['beneficiary']].append(at)
    counts=collections.Counter(len(p) for p in paths.values())
    summary=dict(source=source,events=len(records),distinct_addresses=len(paths),
                 one_event_addresses=counts[1],two_event_addresses=counts[2],
                 eligible_addresses=sum(v for k,v in counts.items() if k>=3),
                 duplicate_address_transaction_logs=duplicates,
                 contract_vs_EOA='not classified; do not interpret addresses as people',
                 scope='Aave Supply/Withdraw or Comet base-asset Supply/Withdraw only; not every protocol interaction')
    return dict(start=manifest['start'],end_exclusive=manifest['end_exclusive'],
                source=source,source_enriched_sha256=manifest['enriched']['sha256'],
                access_paths=[sorted(p) for p in paths.values() if len(p)>=3],
                issuer_schedules=[sorted(set(p)) for p in revocations.values()],summary=summary)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('--private-out',required=True);p.add_argument('--summary',required=True)
    args=p.parse_args();result=normalize(args.folder)
    Path(args.private_out).write_text(json.dumps(result)+'\n');Path(args.summary).write_text(json.dumps(result['summary'],indent=2)+'\n')
