#!/usr/bin/env python3
"""Bounded, read-only fee-history archive; Python standard library only.

No transaction, signing, wallet or state-changing RPC method is permitted.
Network failures produce explicit unavailable metadata, never synthetic fees.
"""

import argparse
import datetime as dt
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


NETWORKS = {
    "ethereum": (1, "ETH_RPC_URL", "https://ethereum-rpc.publicnode.com"),
    "optimism": (10, "OP_RPC_URL", "https://mainnet.optimism.io"),
}
READ_ONLY_METHODS = {"eth_chainId", "eth_getBlockByNumber", "eth_feeHistory"}
PERCENTILES = [10, 50, 90]
MAX_BLOCKS = 7200
MAX_BATCHES = 8


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def iso_timestamp(timestamp):
    return dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).isoformat()


def redact_url(url):
    """Only known public endpoints retain paths; arbitrary paths may contain keys."""
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or "invalid-host"
    if parsed.port:
        host += ":" + str(parsed.port)
    public = {item[2] for item in NETWORKS.values()}
    if url.rstrip("/") in public and not parsed.username and not parsed.query:
        return url.rstrip("/")
    path = "/[path-redacted]" if parsed.path not in ("", "/") else parsed.path
    query = "?[query-redacted]" if parsed.query else ""
    return parsed.scheme + "://" + host + path + query


class CollectionError(Exception):
    pass


def http_worker():
    """Isolated transport: the parent deadline also bounds a stuck DNS lookup."""
    options = json.load(sys.stdin)
    if json.loads(options["body"]).get("method") not in READ_ONLY_METHODS:
        print(json.dumps({"error": "RPC method is not in the read-only allowlist."}))
        return
    request = urllib.request.Request(
        options["url"], data=options["body"].encode(), method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "PETs4DeFi-fee-audit/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=options["timeout"]) as response:
            raw = response.read(16_000_001)
        if len(raw) > 16_000_000:
            raise CollectionError("RPC response exceeded the bounded response size.")
        result = {"payload": json.loads(raw)}
    except urllib.error.HTTPError as exc:
        result = {"error": "RPC HTTP error " + str(exc.code)}
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
        result = {"error": "RPC transport unavailable: " + type(exc).__name__}
    except (ValueError, UnicodeError):
        result = {"error": "RPC returned invalid JSON."}
    except CollectionError as exc:
        result = {"error": str(exc)}
    print(json.dumps(result))


class RPC:
    def __init__(self, url, timeout):
        self.url = url
        self.timeout = timeout
        self.calls = 0
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in ("https", "http") or not parsed.hostname:
            raise CollectionError("Invalid RPC URL; expected http(s).")

    def call(self, method, params):
        if method not in READ_ONLY_METHODS:
            raise CollectionError("RPC method is not in the read-only allowlist.")
        self.calls += 1
        body = json.dumps({"jsonrpc": "2.0", "id": self.calls,
                           "method": method, "params": params})
        try:
            # Send URLs through stdin, not command-line arguments/process logs.
            worker = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--rpc-worker"],
                input=json.dumps({"url": self.url, "body": body, "timeout": self.timeout}),
                text=True, capture_output=True, timeout=self.timeout,
            )
            if worker.returncode != 0:
                raise CollectionError("RPC transport worker failed; details omitted to protect endpoint secrets.")
            envelope = json.loads(worker.stdout)
            if "error" in envelope:
                raise CollectionError(envelope["error"])
            payload = envelope["payload"]
        except subprocess.TimeoutExpired:
            raise CollectionError("RPC transport deadline exceeded (including DNS/proxy lookup).") from None
        except OSError as exc:
            raise CollectionError("RPC transport unavailable: " + type(exc).__name__) from None
        except (ValueError, UnicodeError):
            raise CollectionError("RPC returned invalid JSON.") from None
        if not isinstance(payload, dict) or payload.get("id") != self.calls:
            raise CollectionError("RPC response identity/shape mismatch.")
        if "error" in payload:
            code = payload["error"].get("code") if isinstance(payload["error"], dict) else None
            raise CollectionError("RPC error code " + str(code))
        if "result" not in payload:
            raise CollectionError("RPC result is missing.")
        return payload["result"]


def quantity(value):
    if not isinstance(value, str) or not value.startswith("0x"):
        raise CollectionError("Invalid hexadecimal RPC quantity.")
    try:
        result = int(value, 16)
    except ValueError:
        raise CollectionError("Invalid hexadecimal RPC quantity.") from None
    if result < 0:
        raise CollectionError("Negative RPC quantity.")
    return result


def block_metadata(block):
    if not isinstance(block, dict) or not isinstance(block.get("hash"), str):
        raise CollectionError("Missing block metadata.")
    timestamp = quantity(block.get("timestamp"))
    return {"number": quantity(block.get("number")), "hash": block["hash"],
            "timestamp_unix": timestamp, "timestamp_utc": iso_timestamp(timestamp)}


def decode_history(history, requested_newest, requested_count):
    if not isinstance(history, dict):
        raise CollectionError("Invalid feeHistory result.")
    base = history.get("baseFeePerGas", [])
    ratio = history.get("gasUsedRatio", [])
    rewards = history.get("reward", [])
    count = len(ratio)
    oldest = quantity(history.get("oldestBlock"))
    if not 0 < count <= requested_count or oldest + count - 1 != requested_newest:
        raise CollectionError("feeHistory returned a nonconsecutive or unexpected block range.")
    if len(base) != count + 1 or len(rewards) != count:
        raise CollectionError("feeHistory arrays have inconsistent lengths or missing rewards.")
    # The final base fee is for the NEXT block; deliberately do not count it.
    base_values = [quantity(value) for value in base]
    rows = []
    for offset, (gas_ratio, reward) in enumerate(zip(ratio, rewards)):
        if not isinstance(gas_ratio, (int, float)) or not math.isfinite(gas_ratio) or not 0 <= gas_ratio <= 1:
            raise CollectionError("Invalid gasUsedRatio.")
        if not isinstance(reward, list) or len(reward) != len(PERCENTILES):
            raise CollectionError("Invalid reward percentile array.")
        reward_values = [quantity(value) for value in reward]
        if reward_values != sorted(reward_values):
            raise CollectionError("Reward percentiles are not monotone.")
        base_value = base_values[offset]
        rows.append({
            "block_number": oldest + offset,
            "base_fee_per_gas_wei": str(base_value),
            "gas_used_ratio": gas_ratio,
            "priority_fee_percentiles_wei": dict(zip(map(str, PERCENTILES), map(str, reward_values))),
            "effective_execution_price_percentiles_wei": {
                str(p): str(base_value + r) if gas_ratio > 0 else None
                for p, r in zip(PERCENTILES, reward_values)
            },
        })
    return rows


def distribution(values):
    """Nearest-rank quantiles with ONE observation per included block."""
    ordered = sorted(values)
    if not ordered:
        return {"observations": 0, "p10_wei": None, "p50_wei": None, "p90_wei": None}
    result = {"observations": len(ordered), "min_wei": str(ordered[0]), "max_wei": str(ordered[-1])}
    for percentile in PERCENTILES:
        result["p" + str(percentile) + "_wei"] = str(ordered[max(0, math.ceil(len(ordered) * percentile / 100) - 1)])
    return result


def collect_network(name, args):
    chain_id, environment_key, default_url = NETWORKS[name]
    url = os.environ.get(environment_key, default_url)
    record = {
        "network": name, "status": "unavailable", "source_url": redact_url(url),
        "expected_chain_id": chain_id, "requested_blocks": args.blocks,
        "requested_reward_percentiles": PERCENTILES,
        "collection_started_at_utc": utc_now().isoformat(),
        "raw_fee_history_batches": [], "blocks": [],
    }
    rpc = None
    try:
        rpc = RPC(url, args.timeout)
        observed_chain_id = quantity(rpc.call("eth_chainId", []))
        record["observed_chain_id"] = observed_chain_id
        if observed_chain_id != chain_id:
            raise CollectionError("RPC chain ID does not match the requested network.")
        head = block_metadata(rpc.call("eth_getBlockByNumber", ["latest", False]))
        record["observed_head"] = head
        observed_day = head["timestamp_utc"][:10]
        if args.expected_date and observed_day != args.expected_date:
            raise CollectionError("Head UTC date differs from expected date; not used as a current snapshot.")
        age = utc_now().timestamp() - head["timestamp_unix"]
        record["head_age_seconds_at_collection"] = round(age, 3)
        if age < -300 or age > args.max_head_age:
            raise CollectionError("Head timestamp is stale or in the future relative to collector clock.")
        oldest_needed = max(0, head["number"] - args.blocks + 1)
        cursor = head["number"]
        rows = []
        while cursor >= oldest_needed:
            if len(record["raw_fee_history_batches"]) >= MAX_BATCHES:
                raise CollectionError("Provider returned too few blocks within the eight-batch budget.")
            count = min(1024, cursor - oldest_needed + 1)
            params = [hex(count), hex(cursor), PERCENTILES]
            batch_started = utc_now().isoformat()
            history = rpc.call("eth_feeHistory", params)
            decoded = decode_history(history, cursor, count)
            record["raw_fee_history_batches"].append({
                "requested_at_utc": batch_started, "params": params, "result": history,
            })
            rows.extend(decoded)
            cursor = decoded[0]["block_number"] - 1
        rows.sort(key=lambda item: item["block_number"])
        if [item["block_number"] for item in rows] != list(range(oldest_needed, head["number"] + 1)):
            raise CollectionError("Archived block sequence contains gaps or duplicate blocks.")
        first = block_metadata(rpc.call("eth_getBlockByNumber", [hex(oldest_needed), False]))
        last_check = block_metadata(rpc.call("eth_getBlockByNumber", [hex(head["number"]), False]))
        if first["number"] != oldest_needed or last_check != head:
            raise CollectionError("Pinned block changed during collection; retry to avoid a reorg-mixed snapshot.")
        span = head["timestamp_unix"] - first["timestamp_unix"]
        if span < 0:
            raise CollectionError("Invalid block timestamp order.")
        record["window"] = {
            "first_block": first, "last_block": head, "block_count": len(rows),
            "boundary_timestamp_span_seconds": span,
            "timestamp_note": "Only first/last block timestamps were fetched; individual timestamps are not interpolated.",
        }
        record["blocks"] = rows
        nonempty = [int(row["effective_execution_price_percentiles_wei"]["50"])
                    for row in rows if row["effective_execution_price_percentiles_wei"]["50"] is not None]
        record["summary"] = {
            "base_fee_block_weighted": distribution([int(row["base_fee_per_gas_wei"]) for row in rows]),
            "within_block_effective_p50_block_weighted": distribution(nonempty),
            "empty_blocks_excluded_from_effective_summary": len(rows) - len(nonempty),
        }
        record["status"] = "available"
    except (CollectionError, ValueError, TypeError, KeyError, OverflowError) as exc:
        record["reason"] = str(exc) if isinstance(exc, CollectionError) else "Unexpected RPC data shape: " + type(exc).__name__
        # Raw successful responses remain evidence of a partial attempt, not an accepted snapshot.
        record["blocks"] = []
    record["rpc_call_count"] = rpc.calls if rpc else 0
    record["collection_finished_at_utc"] = utc_now().isoformat()
    return record


def write_snapshot(output, snapshot_path):
    """Keep summary keys stable; archive every full observation losslessly."""
    snapshot_path = Path(snapshot_path)
    archive_name = "fee_history_raw.json.gz" if snapshot_path.stem == "fee_snapshot" else snapshot_path.stem + "_raw.json.gz"
    archive_path = snapshot_path.with_name(archive_name)
    raw_json = (json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    buffer = io.BytesIO()
    # An empty filename and zero mtime avoid machine/path/time-dependent headers.
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=9) as archive:
        archive.write(raw_json)
    compressed = buffer.getvalue()
    summary = {key: value for key, value in output.items() if key != "networks"}
    summary["networks"] = []
    for network in output["networks"]:
        compact = {key: value for key, value in network.items()
                   if key not in {"blocks", "raw_fee_history_batches"}}
        compact["archived_block_count"] = len(network.get("blocks", []))
        compact["archived_fee_history_batch_count"] = len(network.get("raw_fee_history_batches", []))
        summary["networks"].append(compact)
    summary["raw_archive"] = {
        "path": archive_name,
        "path_base": "directory containing this summary",
        "format": "gzip-compressed JSON; complete original snapshot including all raw batches and per-block observations",
        "sha256": hashlib.sha256(compressed).hexdigest(),
        "size_bytes": len(compressed),
        "uncompressed_json_sha256": hashlib.sha256(raw_json).hexdigest(),
        "uncompressed_size_bytes": len(raw_json),
        "gzip_mtime": 0,
    }
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    archive_temp = archive_path.with_suffix(archive_path.suffix + ".tmp")
    archive_temp.write_bytes(compressed)
    archive_temp.replace(archive_path)
    summary_temp = snapshot_path.with_suffix(snapshot_path.suffix + ".tmp")
    summary_temp.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    summary_temp.replace(snapshot_path)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", choices=["all", *NETWORKS], default="all")
    parser.add_argument("--blocks", type=int, default=MAX_BLOCKS)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--expected-date", help="Require latest block UTC date YYYY-MM-DD; no historical lookup is implied.")
    parser.add_argument("--max-head-age", type=int, default=3600, help="Maximum current-head age in seconds.")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "results" / "fee_snapshot.json")
    args = parser.parse_args()
    if not 1 <= args.blocks <= MAX_BLOCKS or not 0 < args.timeout <= 30 or args.max_head_age < 1:
        parser.error("blocks must be 1..7200, timeout >0 and <=30, max-head-age positive")
    if args.expected_date:
        try:
            if dt.date.fromisoformat(args.expected_date).isoformat() != args.expected_date:
                raise ValueError
        except ValueError:
            parser.error("expected-date must have format YYYY-MM-DD")
    names = list(NETWORKS) if args.network == "all" else [args.network]
    output = {
        "schema_version": 1, "collected_at_utc": utc_now().isoformat(),
        "expected_head_utc_date": args.expected_date,
        "methodology": {
            "rpc_methods": sorted(READ_ONLY_METHODS),
            "read_only": True, "max_fee_history_calls_per_network": MAX_BATCHES,
            "raw_reward_metric": "Within-block gas-used-weighted effective priority fee percentiles (10/50/90).",
            "effective_metric": "Block base fee plus within-block priority fee percentile; execution only.",
            "summary_metric": "Nearest-rank block-weighted distribution of within-block effective p50 values; NOT global transaction percentiles.",
            "op_limit": "OP execution-price proxy only: L1 data/operator fees are excluded. Deposits/system transactions can follow different fee rules; this is not their actual paid-price distribution or total OP transaction cost.",
            "window_limit": "7200 Ethereum blocks are about 24 hours; 7200 OP blocks are about 4 hours. Exact boundary span is recorded.",
            "unverified_external_claims": "The supplied 0.067 and 0.38 gwei figures have no verified timestamp/window/metric here; they are not calibration inputs.",
        },
        "networks": [collect_network(name, args) for name in names],
    }
    output["status"] = "available" if all(item["status"] == "available" for item in output["networks"]) else "partial" if any(item["status"] == "available" for item in output["networks"]) else "unavailable"
    write_snapshot(output, args.output)
    for result in output["networks"]:
        print(result["network"] + ": " + result["status"] + (" — " + result["reason"] if "reason" in result else ""))
    return 0 if output["status"] == "available" else 2


if __name__ == "__main__":
    if sys.argv[1:] == ["--rpc-worker"]:
        http_worker()
    else:
        raise SystemExit(main())
