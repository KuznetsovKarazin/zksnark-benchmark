"""Classify historical Base account bytecode. The per-address cache stays private."""
import argparse
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import NamedTemporaryFile

from access_paths import load_paths

ENDPOINT = os.environ.get("BASE_RPC_URL") or "https://base-rpc.publicnode.com"
ZERO = "0x" + "00" * 20
POOL = "0xa238dd80c259a72e81d7e4664a9801593f98d1c5"
BATCH = 40


def rpc(payload):
    request = urllib.request.Request(
        ENDPOINT, json.dumps(payload).encode(),
        {"Content-Type": "application/json", "User-Agent": "ECON08-aggregate-research/1"},
    )
    with urllib.request.urlopen(request, timeout=22) as response:
        return json.load(response)


def call(method, params):
    reply = rpc({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    if reply.get("result") is None:
        raise ValueError("Missing RPC result for " + method)
    return reply["result"]


def code_kind(value):
    if not isinstance(value, str) or not value.startswith("0x") or len(value) % 2:
        return "unknown"
    try:
        raw = bytes.fromhex(value[2:])
    except ValueError:
        return "unknown"
    if not raw:
        return "empty"
    if len(raw) == 23 and raw[:3] == bytes.fromhex("ef0100"):
        return "delegated"
    return "other_code"


def fetch_chunk(addresses, block):
    known = {}
    pending = list(addresses)
    for attempt in range(3):
        payload = [{"jsonrpc": "2.0", "method": "eth_getCode", "id": i + 1, "params": [a, block]}
                   for i, a in enumerate(pending)]
        try:
            response = rpc(payload)
            if not isinstance(response, list):
                raise ValueError("Expected batch of code replies")
            ids = [r.get("id") for r in response]
            if len(ids) != len(set(ids)) or not set(ids).issubset(range(1, len(pending) + 1)):
                raise ValueError("Inconsistent response IDs")
            for r in response:
                kind = code_kind(r.get("result"))
                if kind != "unknown":
                    known[pending[r["id"] - 1]] = kind
        except (OSError, ValueError):
            pass
        pending = [a for a in pending if a not in known]
        if not pending:
            break
        if attempt < 2:
            time.sleep(2 ** attempt)
    return {a: known.get(a, "unknown") for a in addresses}


def store(path, payload):
    with NamedTemporaryFile("w", dir=path.parent, delete=False) as out:
        json.dump(payload, out, sort_keys=True, separators=(",", ":"))
        tmp = out.name
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-aave", required=True, type=Path)
    parser.add_argument("--private-code-cache", required=True, type=Path)
    args = parser.parse_args()
    paths, _, _, last = load_paths(args.private_aave)
    path = args.private_code_cache
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.stat().st_mode & 0o077:
        raise ValueError("Use an owner-only directory for the local account-code cache")
    block, block_hash = hex(last["end_block"]), last["last_hash"]

    def verify_anchor():
        if int(call("eth_chainId", []), 16) != 8453:
            raise ValueError("Unexpected chain")
        if call("eth_getBlockByNumber", [block, False])["hash"] != block_hash:
            raise ValueError("Closing block differs from the original coverage record")
        if code_kind(call("eth_getCode", [POOL, block])) != "other_code":
            raise ValueError("Historical Aave Pool control failed")
        if code_kind(call("eth_getCode", [ZERO, block])) != "empty":
            raise ValueError("Historical empty-code control failed")

    verify_anchor()
    data = {"block_hash": block_hash, "block_number": last["end_block"], "kinds": {}}
    if path.exists():
        data = json.loads(path.read_text())
        if (data["block_hash"], data["block_number"]) != (block_hash, last["end_block"]):
            raise ValueError("Cache belongs to another snapshot")
        if not set(data["kinds"]) <= set(paths):
            raise ValueError("Cache contains addresses outside the eligible window")
    pending = sorted(a for a in paths if data["kinds"].get(a, "unknown") == "unknown")
    batches = [pending[i:i + BATCH] for i in range(0, len(pending), BATCH)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for i, chunk in enumerate(pool.map(lambda addresses: fetch_chunk(addresses, block), batches), 1):
            data["kinds"].update(chunk)
            if i % 20 == 0:
                store(path, data)
                print("Completed batches", i, "of", len(batches), flush=True)
    verify_anchor()
    store(path, data)
    print("Classified", sum(k != "unknown" for k in data["kinds"].values()), "of", len(paths))


if __name__ == "__main__":
    main()
