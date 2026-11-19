#!/usr/bin/env python3
"""Read-only, resumable JSON-RPC log acquisition. Python standard library only.

Raw replies stay in the caller-selected private directory. A failed request is
an incomplete range, NEVER evidence of zero events. UTC end is exclusive.
"""
import argparse
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import urllib.error

REVOKED = "0xf930a6e2523c9cc298691873087a740550b8fc85a0680830414c148ed927f615"
SUPPLY_AAVE = "0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61"
WITHDRAW_AAVE = "0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7"
SUPPLY_COMET = "0xd1cf3d156d5f8f0d50f6c122ed609cec09d35c9b9fb3fff6ea0959134dae424e"
WITHDRAW_COMET = "0x9b1bfa7fa9ee420a16e124f794c35ac9f90472acc99140eb2f6447c714cad8eb"
SOURCES = {
    "eas_ethereum": (1, "https://ethereum-rpc.publicnode.com", "0xA1207F3BBa224E2c9c3c6D5aF63D0eb1582Ce587", [REVOKED]),
    "eas_base": (8453, "https://base-rpc.publicnode.com", "0x4200000000000000000000000000000000000021", [REVOKED]),
    "eas_optimism": (10, "https://optimism-rpc.publicnode.com", "0x4200000000000000000000000000000000000021", [REVOKED]),
    "aave_base": (8453, "https://base-rpc.publicnode.com", "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5", [SUPPLY_AAVE, WITHDRAW_AAVE]),
    "compound_base": (8453, "https://base-rpc.publicnode.com", "0xb125E6687d4313864e53df431d5425969c15Eb2F", [SUPPLY_COMET, WITHDRAW_COMET]),
}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def rpc(url, method, params, retries=2):
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, canonical(request), {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as response:
                result = json.load(response)
            if "error" in result:
                raise RuntimeError(str(result["error"]))
            if "result" not in result or result["result"] is None:
                raise RuntimeError("Missing RPC result")
            return result["result"]
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403) or attempt == retries:
                raise
            time.sleep(0.3 * (attempt + 1))
        except Exception:
            if attempt == retries:
                raise
            time.sleep(0.3 * (attempt + 1))


def timestamp(iso):
    return int(dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def block_boundary(url, target, high):
    """First block with timestamp >= target; no assumed constant block spacing."""
    tip = rpc(url, "eth_getBlockByNumber", [hex(high), False])
    recent = rpc(url, "eth_getBlockByNumber", [hex(max(0, high - 1024)), False])
    interval = max(0.01, (int(tip["timestamp"], 16) - int(recent["timestamp"], 16)) / 1024)
    # Establish a recent bracket before binary search. Querying halfway to genesis
    # needlessly requires very old archive access on otherwise useful RPC nodes.
    span = max(2048, int((int(tip["timestamp"], 16) - target) / interval * 1.1) + 2048)
    low = max(0, high - span)
    while low > 0:
        block = rpc(url, "eth_getBlockByNumber", [hex(low), False])
        if int(block["timestamp"], 16) < target:
            break
        span *= 2
        low = max(0, high - span)
    while low < high:
        mid = (low + high) // 2
        block = rpc(url, "eth_getBlockByNumber", [hex(mid), False])
        if int(block["timestamp"], 16) < target:
            low = mid + 1
        else:
            high = mid
    return low


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n")


def acquire(name, out, start, end, chunk=40000, workers=3):
    chain, url, address, topics = SOURCES[name]
    out = Path(out) / name
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if (manifest["start"], manifest["end_exclusive"]) != (start, end):
            raise ValueError("Refusing to mix different acquisition windows")
        first, stop = manifest["first_block"], manifest["stop_block_exclusive"]
    else:
        chain_actual = int(rpc(url, "eth_chainId", []), 16)
        if chain_actual != chain:
            raise ValueError("RPC chain mismatch")
        tip = rpc(url, "eth_getBlockByNumber", ["finalized", False])
        if int(tip["timestamp"], 16) < timestamp(end):
            raise RuntimeError("Requested window is not yet finalized")
        height = int(tip["number"], 16)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f = pool.submit(block_boundary, url, timestamp(start), height)
            g = pool.submit(block_boundary, url, timestamp(end), height)
            first, stop = f.result(), g.result()
        manifest = dict(source=name, chain_id=chain, rpc=url, address=address, topics=topics,
                        start=start, end_exclusive=end, first_block=first,
                        stop_block_exclusive=stop, finalized_tip=tip["hash"],
                        retrieved_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                        complete=False, chunks=[], errors=[])
        save_json(manifest_path, manifest)

    def fetch(pair):
        lo, hi = pair
        file = out / "chunks" / f"{lo}-{hi}.json.gz"
        if file.exists():
            payload = json.loads(gzip.decompress(file.read_bytes()))
            if payload["request"]["fromBlock"] != hex(lo) or payload["request"]["toBlock"] != hex(hi):
                raise ValueError("Cached range mismatch")
        else:
            filt = {"address": address, "topics": [topics[0] if len(topics) == 1 else topics], "fromBlock": hex(lo), "toBlock": hex(hi)}
            try:
                logs = rpc(url, "eth_getLogs", [filt])
            except Exception as exc:
                # Providers may cap range or response size. Split, but never silently
                # substitute an empty response. Bounded leaves prevent retry storms.
                is_access_error = isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403)
                if hi - lo > 4999 and not is_access_error:
                    mid = (lo + hi) // 2
                    return fetch((lo, mid)) + fetch((mid + 1, hi))
                return [dict(first=lo, last=hi, error=str(exc))]
            if not isinstance(logs, list):
                raise ValueError("Invalid logs response")
            payload = {"request": filt, "logs": logs}
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(gzip.compress(canonical(payload), mtime=0))
        return [dict(first=lo, last=hi, path=str(file.relative_to(out)), count=len(payload["logs"]),
                     sha256=hashlib.sha256(file.read_bytes()).hexdigest())]

    ranges = [(lo, min(lo + chunk - 1, stop - 1)) for lo in range(first, stop, chunk)]
    entries = fetch(ranges[0]) if ranges else []
    if any('error' in x for x in entries):
        manifest['errors'] = [x for x in entries if 'error' in x]
        manifest['complete'] = False
        manifest['unattempted_ranges'] = len(ranges) - 1
        save_json(manifest_path, manifest)
        print(json.dumps({'source': name, 'complete': False, 'errors': manifest['errors'], 'unattempted_ranges': len(ranges)-1}), flush=True)
        return manifest
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for i, result in enumerate(pool.map(fetch, ranges[1:])):
            entries.extend(result)
            if i % 10 == 0:
                print(json.dumps({"source": name, "ranges_done": i + 1, "ranges_total": len(ranges)}), flush=True)
    manifest["chunks"] = sorted([x for x in entries if "error" not in x], key=lambda x: x["first"])
    manifest["errors"] = [x for x in entries if "error" in x]
    manifest["complete"] = not manifest["errors"]
    manifest["raw_log_count"] = sum(x["count"] for x in manifest["chunks"])
    save_json(manifest_path, manifest)
    print(json.dumps({k: manifest[k] for k in ("source", "complete", "raw_log_count")}), flush=True)
    return manifest


def load_logs(folder):
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text())
    if not manifest["complete"]:
        raise ValueError("Incomplete coverage: cannot infer population rates or gate failure")
    expected = manifest["first_block"]
    unique = {}
    for chunk in manifest["chunks"]:
        if chunk["first"] != expected:
            raise ValueError("Gap or overlap in coverage")
        expected = chunk["last"] + 1
        raw = (folder / chunk["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != chunk["sha256"]:
            raise ValueError("Corrupt cached source")
        for row in json.loads(gzip.decompress(raw))["logs"]:
            if row.get("removed", False):
                raise ValueError("Removed/reorg log")
            block = int(row["blockNumber"], 16)
            if not chunk["first"] <= block <= chunk["last"]:
                raise ValueError("Out-of-range log")
            if row["address"].lower() != manifest["address"].lower():
                raise ValueError("Wrong source contract")
            if row["topics"][0].lower() not in manifest["topics"]:
                raise ValueError("Wrong event topic")
            key = (row["blockHash"], row["transactionHash"], row["logIndex"])
            if key in unique and unique[key] != row:
                raise ValueError("Conflicting duplicate log")
            unique[key] = row
    if expected != manifest["stop_block_exclusive"]:
        raise ValueError("Incomplete terminal range")
    rows = sorted(unique.values(), key=lambda r: (int(r["blockNumber"], 16), int(r["transactionIndex"], 16), int(r["logIndex"], 16)))
    return manifest, rows


def enrich(folder, workers=4):
    """Resolve real block timestamps and validate every log's block hash."""
    folder = Path(folder)
    manifest, logs = load_logs(folder)
    numbers = sorted({int(r["blockNumber"], 16) for r in logs})
    cache = folder.parent / f"blocks-{manifest['chain_id']}"
    cache.mkdir(exist_ok=True)
    def one(number):
        file = cache / f"{number}.json"
        if file.exists():
            block = json.loads(file.read_text())
        else:
            raw = rpc(manifest["rpc"], "eth_getBlockByNumber", [hex(number), False])
            block = {k: raw[k] for k in ("number", "hash", "timestamp", "parentHash")}
            save_json(file, block)
        if int(block["number"], 16) != number:
            raise ValueError("Block number mismatch")
        return number, block
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        blocks = dict(pool.map(one, numbers))
    result = []
    for row in logs:
        header = blocks[int(row["blockNumber"], 16)]
        if header["hash"].lower() != row["blockHash"].lower():
            raise ValueError("Reorg or mismatching block header")
        ts = int(header["timestamp"], 16)
        if not timestamp(manifest["start"]) <= ts < timestamp(manifest["end_exclusive"]):
            raise ValueError("Timestamp outside frozen window")
        result.append(dict(row, timestamp=ts))
    target = folder / "enriched_logs.json.gz"
    target.write_bytes(gzip.compress(canonical(result), mtime=0))
    manifest["enriched"] = dict(count=len(result), blocks=len(blocks), sha256=hashlib.sha256(target.read_bytes()).hexdigest(), all_block_hashes_checked=True)
    save_json(folder / "manifest.json", manifest)
    print(json.dumps({"source": manifest["source"], "enriched": len(result), "blocks": len(blocks)}), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source", choices=SOURCES)
    p.add_argument("--out", required=True)
    p.add_argument("--protocol", default=str(Path(__file__).parents[1] / "config/protocol.json"))
    p.add_argument("--enrich", action="store_true")
    args = p.parse_args()
    spec = json.loads(Path(args.protocol).read_text())
    m = acquire(args.source, args.out, spec["window_start"], spec["window_end_exclusive"])
    if args.enrich and m["complete"]:
        enrich(Path(args.out) / args.source)
