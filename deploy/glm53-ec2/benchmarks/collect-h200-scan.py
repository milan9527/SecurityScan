#!/usr/bin/env python3
"""Summarize real scan traffic; separate inference throughput from scan throughput."""
import argparse
import html
import json
import shutil
import statistics
from collections import Counter
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--out", type=Path, required=True)
parser.add_argument("--runs", type=Path, required=True)
parser.add_argument("--target", required=True)
args = parser.parse_args()
status = json.loads((args.out / "status.json").read_text())
records = [json.loads(line) for line in (args.out / "wire-metrics.jsonl").read_text().splitlines()]
records = [r for r in records if status["start_epoch"] <= r["start_epoch"] <= status["end_epoch"]]
good = [r for r in records if r.get("completed") and r.get("status") == 200 and r.get("streaming")]


def dist(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    def q(p):
        i = (len(values) - 1) * p
        lo = int(i)
        return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (i - lo)
    return {"n": len(values), "mean": statistics.mean(values), "p50": q(.5), "p95": q(.95)}


tokens = sum((r.get("usage") or {}).get("completion_tokens") or 0 for r in good)
coverage = sum((r.get("usage") or {}).get("completion_tokens") is not None for r in good)
complete_usage = bool(good) and coverage == len(good)
window = max((r["end_epoch"] for r in good), default=0) - min((r["start_epoch"] for r in good), default=0)
summary = {
    "hardware": "p5en.48xlarge / 8 x NVIDIA H200 / TP8",
    "model": "GLM-5.3 / SGLang / MTP 3/1/4",
    "serving_config": {
        "region": "ap-northeast-1", "sglang_version": "0.5.23",
        "tensor_parallel_size": 8, "context_length": 262144,
        "max_running_requests": 2, "mem_fraction_static": 0.80,
        "chunked_prefill_size": 8192, "kv_cache_dtype": "fp8_e4m3",
        "max_output_tokens": 32768, "reasoning_effort": "low",
    },
    "scan_status": status, "attempts": len(records), "successful_streams": len(good),
    "failed_attempts": sum(
        not r.get("completed") or r.get("status") != 200 for r in records),
    "target_commit": (args.out / "target-sha.txt").read_text().strip(),
    "complete_scan": False,
    "non_streaming_requests_excluded_from_model_metrics": sum(
        not r.get("streaming") for r in records),
    "usage_coverage": coverage,
    "token_metric_scope": "successful_streaming_requests_only; non-streaming output tokens are not captured",
    "ttft_ms": dist([r.get("ttft_ms") for r in good]),
    "visible_ttft_ms": dist([r.get("visible_ttft_ms") for r in good]),
    "request_e2e_ms": dist([r["e2e_ms"] for r in good]),
    "output_tokens": tokens,
    "model_traffic_window_s": window,
    "output_tokens_per_traffic_window_second": tokens / window if complete_usage and window > 0 else None,
    "output_tokens_per_scan_second": tokens / status["elapsed_s"] if complete_usage and status["elapsed_s"] else None,
    "request_output_tokens_per_second": dist([
        r["usage"]["completion_tokens"] / (r["e2e_ms"] / 1000)
        for r in good if (r.get("usage") or {}).get("completion_tokens") is not None
        and r["e2e_ms"] > 0]),
}
for path in args.runs.glob("*/run.json"):
    run = json.loads(path.read_text())
    if any(t.get("original") == args.target for t in run.get("targets_info", [])):
        if status["start_epoch"] <= path.stat().st_mtime <= status["end_epoch"] + 5:
            shutil.copytree(path.parent, args.out / "strix-runs" / path.parent.name, dirs_exist_ok=True)
            summary["strix"] = {k: run.get(k) for k in ["run_id", "status"]}
            summary["strix"]["llm_usage"] = {
                k: v for k, v in (run.get("llm_usage") or {}).items()
                if isinstance(v, (int, float, bool)) or v is None
            }
            summary["strix"]["tool_calls"] = len(run.get("tool_calls", []))
            findings_path = path.parent / "vulnerabilities.json"
            if findings_path.exists():
                findings = json.loads(findings_path.read_text())
                summary["strix"]["unverified_findings"] = len(findings)
                summary["strix"]["severity_counts"] = dict(Counter(
                    item.get("severity", "unknown") for item in findings))
            summary["complete_scan"] = (
                run.get("status") == "completed" and status["exit_code"] in (0, 2)
            )
(args.out / "performance-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
def number(value):
    return "未测得" if value is None else f"{value:.3f}"

rows = []
for label, key in [("TTFT", "ttft_ms"), ("模型请求 E2E", "request_e2e_ms")]:
    d = summary[key] or {}
    rows.append(f"| {label}（秒） | " + " | ".join(
        number(d[k] / 1000 if k in d else None) for k in ["mean", "p50", "p95"]) + " |")
table = "\n".join(rows)
headline = f"""
扫描状态：{'完整完成' if summary['complete_scan'] else '未完整完成'}；扫描 E2E：{status['elapsed_s']} 秒。
成功流式请求：{len(good)}；失败请求：{summary['failed_attempts']}。

| 指标 | 均值 | P50 | P95 |
| --- | ---: | ---: | ---: |
{table}

8 卡已采集流式输出吞吐：流式流量时间窗口 **{number(summary['output_tokens_per_traffic_window_second'])} tokens/s**；
已采集流式输出 token / 整次扫描耗时 **{number(summary['output_tokens_per_scan_second'])} tokens/s**。
两者均包含相应时间窗口内的工具与编排间隔，不是 GPU 连续解码速度。
"""
text = """# H200 实际 Strix 扫描性能

机型：p5en.48xlarge，8 × H200，GLM-5.3 TP8，MTP 3/1/4。

""" + headline + """
TTFT：控制端代理向上游发出请求至首个非空 reasoning/content/tool 增量抵达；首段可见正文另列。
模型请求 E2E：请求发出至响应读完，包含排队、推理和 SSM 网络开销。
扫描 E2E：包含 Strix 编排、模型与工具调用，不含模型权重加载。
吞吐量为 8 卡整体，不是单卡；输出 token 使用服务端 usage（含 reasoning）。
请求吞吐量、首个至最后一个成功流式请求的时间窗口吞吐量、流式 token / 整次扫描耗时分别列出。
如果 usage_coverage 少于 successful_streams，token 吞吐量不完整，不能直接比较。
Strix 自带首事件计时不作为此处 TTFT。自动发现仍需独立核验。
所有非流式请求（包括连通性预检）均不计入模型性能分布，但包含在扫描整体耗时与 attempts 中。
当前代理未采集非流式输出 token，因此上述 token 总数与吞吐量只覆盖成功流式请求，不代表全部扫描输出。
若 complete_scan 为 false，以下指标仅描述中断前的部分流量，不代表完整扫描成绩。

```json
""" + json.dumps(summary, indent=2, ensure_ascii=False) + "\n```\n"
(args.out / "README.md").write_text(text)
(args.out / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>H200 Strix 性能</title>'
    '<style>body{max-width:1000px;margin:40px auto;font:16px/1.6 system-ui}pre{white-space:pre-wrap}</style>'
    '<pre>' + html.escape(text) + '</pre>')
