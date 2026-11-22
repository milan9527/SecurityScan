#!/usr/bin/env python3
"""Collect only this suite's new Strix runs and retain original evidence."""
import argparse
import json
import shutil
import statistics
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--runs", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
parser.add_argument("--target", help="Exact repository target for multi-scenario audits")
args = parser.parse_args()
timing_file = args.out / ("timing.jsonl" if args.target else "strix-timing.jsonl")
timings = [json.loads(line) for line in timing_file.read_text().splitlines()]


def distribution(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    def q(fraction):
        position = (len(values) - 1) * fraction
        low = int(position)
        return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (position - low)
    return {"n": len(values), "mean": statistics.mean(values), "p50": q(.5), "p95": q(.95)}


results = []
for timing in timings:
    case = timing["scenario"]
    candidates = []
    for path in args.runs.glob("*/run.json"):
        run = json.loads(path.read_text())
        targets = [t.get("original", "") for t in run.get("targets_info", [])]
        if any(t == args.target if args.target else t.endswith("/benchmarks/fixtures/" + case) for t in targets):
            if timing["start_epoch"] <= path.stat().st_mtime < timing["end_epoch"] + 1:
                candidates.append((path, run))
    if not candidates:
        results.append({**timing, "error": "No matching run record"})
        continue
    path, run = max(candidates, key=lambda pair: pair[0].stat().st_mtime)
    destination = args.out / "strix-runs" / path.parent.name
    shutil.copytree(path.parent, destination, dirs_exist_ok=True)
    requests = run.get("llm_requests", [])
    results.append({
        **timing, "run_id": run.get("run_id"), "status": run.get("status"),
        "scan_completed": run.get("scan_results", {}).get("scan_completed"),
        "llm_usage": run.get("llm_usage"), "request_attempts": len(requests),
        "outcomes": {outcome: sum(r.get("outcome") == outcome for r in requests)
                     for outcome in sorted({str(r.get("outcome")) for r in requests})},
        "request_latency_ms": distribution([r.get("duration_ms") for r in requests]),
        "ttft_ms": distribution([r.get("ttft_ms") for r in requests]),
        "evidence": str(destination),
    })
(args.out / "strix-summary.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps([{k: v for k, v in r.items() if k != "llm_usage"} for r in results], indent=2))
