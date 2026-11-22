#!/usr/bin/env python3
"""Aggregate retained measurements without excluding errors from raw evidence."""
import argparse
import json
import statistics
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("metrics", type=Path)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
rows = [json.loads(line) for line in args.metrics.read_text().splitlines() if line]
requests = [r for r in rows if r.get("type") != "summary" and not r.get("warmup")]


def distribution(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None

    def percentile(q):
        position = (len(values) - 1) * q
        low = int(position)
        return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (position - low)

    return {"n": len(values), "mean": statistics.mean(values),
            "p50": percentile(.5), "p95": percentile(.95)}


groups = []
for concurrency in sorted({r["concurrency"] for r in requests}):
    for case in sorted({r["case"] for r in requests}):
        selected = [r for r in requests if r["concurrency"] == concurrency and r["case"] == case]
        group = {"case": case, "concurrency": concurrency, "requests": len(selected),
                 "errors": sum(r["error"] is not None for r in selected),
                 "truncated": sum("length" in r["finish_reasons"] for r in selected),
                 "no_visible_answer": sum(not r.get("answer", "").strip() for r in selected),
                 "completed_with_answer": sum(
                     not r["error"] and "stop" in r["finish_reasons"]
                     and bool(r.get("answer", "").strip()) for r in selected)}
        for metric in ("ttft_s", "first_visible_s", "ttot_s", "e2e_s", "approx_tpot_s"):
            group[metric] = distribution([r[metric] for r in selected])
        for metric in ("prompt_tokens", "completion_tokens"):
            group[metric] = distribution([r["usage"].get(metric) for r in selected])
        groups.append(group)
result = {"stages": [r for r in rows if r.get("type") == "summary"], "scenarios": groups}
args.out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
