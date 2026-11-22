#!/usr/bin/env python3
"""Sequential deep scans with durable progress and evidence, independent of chat."""
import collections
import datetime
import html
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
CASES = [
    ("agentcoreshell-deep", "/home/ec2-user/bedrock/AgentcoreShell", HERE / "superagent/full.txt"),
    ("superagent-frontend-deployment", "/home/ec2-user/bedrock/agentcore-superagent-update",
     HERE / "superagent/frontend-deployment.txt"),
]
results = []


def atomic(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def report():
    snapshot = {"updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "cases": results, "ec2": "Keep running", "ttft_measured": False}
    atomic(OUT / "progress.json", json.dumps(snapshot, indent=2) + "\n")
    text = "# GLM-5.3 additional full Strix scans\n\n"
    text += "Self-hosted GLM-5.3 / SGLang / TP8 / MTP / p6-b200.48xlarge.\n\n"
    text += "Deep mode; full scope; sequential scans to avoid cross-scan contention.\n\n"
    text += "Non-streaming request latency is not TTFT or streaming TTOT. Findings require independent verification. EC2 remains running.\n\n"
    for r in results:
        text += f"## {r['case']}\n\n```json\n{json.dumps(r, indent=2)}\n```\n\n"
    atomic(OUT / "README.md", text)
    atomic(OUT / "report.html", '<!doctype html><html lang="en"><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1">'
           '<title>Additional Strix scans</title><style>body{max-width:1100px;margin:40px auto;'
           'padding:20px;font:16px/1.6 system-ui}pre{white-space:pre-wrap}</style><body><pre>'
           + html.escape(text) + "</pre></body></html>")


for name, target, instructions in CASES:
    out = OUT / name
    out.mkdir()
    previous = set((ROOT / "strix-src/strix_runs").glob("*/run.json"))
    started = time.time()
    row = {"case": name, "target": target, "status": "starting"}
    results.append(row)
    shutil.copyfile(instructions, out / "instructions.txt")
    env = dict(os.environ, STRIX_TARGET=target, STRIX_REPORT_DIR=str(out),
               STRIX_INSTRUCTION_FILE=str(instructions))
    with (out / "runner.log").open("w") as log:
        process = subprocess.Popen(["bash", str(HERE / "run-full-superagent.sh")],
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        run_path = None
        while True:
            code = process.poll()
            row.update(elapsed_s=round(time.time() - started), runner_pid=process.pid)
            for path in set((ROOT / "strix-src/strix_runs").glob("*/run.json")) - previous:
                try:
                    run = json.loads(path.read_text())
                    if not any(t.get("original") == target for t in run.get("targets_info", [])):
                        continue
                    run_path = path
                    requests = run.get("llm_requests", [])
                    durations = sorted(r["duration_ms"] for r in requests
                                       if isinstance(r.get("duration_ms"), (int, float)))
                    findings_path = path.parent / "vulnerabilities.json"
                    findings = json.loads(findings_path.read_text()) if findings_path.exists() else []
                    row.update(status=run.get("status"), run_id=run.get("run_id"),
                               requests=len(requests), outcomes=dict(collections.Counter(
                                   r.get("outcome", "unknown") for r in requests)),
                               tool_calls=len(run.get("tool_calls", [])), unverified_findings=len(findings),
                               severity=dict(collections.Counter(f.get("severity", "unknown") for f in findings)),
                               request_mean_ms=statistics.mean(durations) if durations else None,
                               request_p95_ms=durations[min(len(durations)-1, int(.95*len(durations)))]
                               if durations else None)
                except (FileNotFoundError, json.JSONDecodeError):
                    continue
            if code is not None:
                row["exit_code"] = code
                row["runner_finished"] = True
                if run_path:
                    shutil.copytree(run_path.parent, out / "evidence", dirs_exist_ok=True)
                else:
                    row["status"] = "failed_without_run_record"
                report()
                break
            report()
            time.sleep(20)
atomic(OUT / "suite-status.json", json.dumps({"finished": True, "cases": results}, indent=2) + "\n")
