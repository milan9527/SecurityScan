#!/usr/bin/env python3
"""Persist full-scan progress independently of the interactive session."""
import argparse
import collections
import datetime
import html
import json
from pathlib import Path
import shutil
import statistics
import time


def write_atomic(path, text):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def summarize(out, run_path):
    records = [json.loads(line) for line in
               (out / "stream-metrics.jsonl").read_text().splitlines()]
    benchmarks = [r for r in records if r.get("type") == "summary"]
    run = json.loads(run_path.read_text())
    requests = run.get("llm_requests", [])
    durations = [r["duration_ms"] for r in requests
                 if isinstance(r.get("duration_ms"), (int, float))]
    status_path = out / "status.json"
    terminal = status_path.exists()
    status = json.loads(status_path.read_text()) if terminal else None
    findings_path = run_path.parent / "vulnerabilities.json"
    findings = json.loads(findings_path.read_text()) if findings_path.exists() else []
    severities = dict(collections.Counter(f.get("severity", "unknown") for f in findings))
    completed_with_findings = (
        run.get("status") == "completed" and bool(findings)
        and status is not None and status.get("exit_code") == 2
    )
    snapshot = {
        "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": "self-hosted GLM-5.3, SGLang TP8 MTP, p6-b200.48xlarge",
        "benchmark": benchmarks,
        "scan": {
            "run_id": run.get("run_id"), "status": run.get("status"),
            "runner_status": status,
            "completed_with_findings": completed_with_findings,
            "findings_count": len(findings),
            "findings_by_severity": severities,
            "findings_validation": "Not independently verified",
            "request_attempts": len(requests),
            "outcomes": dict(collections.Counter(r.get("outcome", "unknown") for r in requests)),
            "request_latency_mean_ms": statistics.mean(durations) if durations else None,
            "tool_calls": len(run.get("tool_calls", [])),
            "evidence": str(run_path.parent),
        },
        "ec2_lifecycle": "Keep running per user instruction; this reporter has no AWS mutations.",
    }
    write_atomic(out / "progress-summary.json", json.dumps(snapshot, indent=2) + "\n")
    lines = [
        "# GLM-5.3 完整 Strix 测试",
        "", f"更新时间（UTC）：{snapshot['observed_utc']}",
        "", "模型：自建 GLM-5.3 / SGLang TP8 / MTP / p6-b200.48xlarge。",
        "", f"扫描状态：{run.get('status')}；扫描进程已结束：{terminal}。",
        f"模型请求：{len(requests)}；结果：{snapshot['scan']['outcomes']}。",
        f"工具调用：{snapshot['scan']['tool_calls']}。",
        f"自动发现：{len(findings)} 条（待独立核验）；严重程度：{severities}。",
        *([f"扫描用时：{status.get('elapsed_s')} 秒。"] if status else []),
        *(["退出码 2：扫描已完成，发现达到 fail-on 阈值的问题；不是模型调用失败。"]
          if completed_with_findings else []),
        *([f"完整扫描模型请求平均延迟：{statistics.mean(durations) / 1000:.3f} 秒。"]
          if durations else []),
        "", "## 已完成的独立流式性能测试",
        "", "| 并发 | 请求数 | TTFT 平均秒 | 首段可见正文平均秒 | TTOT 平均秒 | TTOT P95 秒 | 总输出 token/s | 错误/截断 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for b in benchmarks:
        lines.append(
            f"| {b['concurrency']} | {b['requests']} | {b['ttft_s']['mean']:.3f} | "
            f"{b['first_visible_s']['mean']:.3f} | {b['ttot_s']['mean']:.3f} | "
            f"{b['ttot_s']['p95']:.3f} | {b['output_tokens_per_s']:.1f} | "
            f"{b['errors']}/{b['truncated']} |")
    lines.extend([
        "", "场景：认证、路径处理、webhook、工具调用；每场景重复 3 次，分别测试并发 1 和 2。",
        "TTFT 包括 reasoning/content/tool 的首个非空增量；可见正文时间单独统计。",
        "TTOT 为请求开始至最后一个生成增量；吞吐量包含 reasoning token，并发吞吐为合计值。",
        "测量包含 SSM 隧道开销。每组仅 12 个样本，P95 仅供参考。",
        "", "完整 Strix 扫描使用非流式调用，其请求延迟不能作为上述流式 TTFT。",
        "扫描生成的漏洞报告仍需核验，不能将报告数量直接视为已确认漏洞数量。",
        "", "EC2 按用户最新要求保持运行。",
    ])
    text = "\n".join(lines) + "\n"
    write_atomic(out / "README.md", text)
    write_atomic(out / "report.html",
                 '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
                 '<meta name="viewport" content="width=device-width,initial-scale=1">'
                 '<title>GLM-5.3 Strix 测试</title>'
                 '<style>body{max-width:1100px;margin:40px auto;padding:20px;'
                 'font:16px/1.6 system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
                 '<body><pre>' + html.escape(text) + '</pre></body></html>')
    if terminal:
        shutil.copytree(run_path.parent, out / "strix-runs" / run_path.parent.name,
                        dirs_exist_ok=True)
    return terminal


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    while True:
        try:
            finished = summarize(args.out, args.run)
            if finished or not args.watch:
                break
        except (json.JSONDecodeError, FileNotFoundError):
            if not args.watch:
                raise
        time.sleep(30)
