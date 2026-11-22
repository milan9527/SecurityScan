#!/usr/bin/env python3
"""Render the H200 comparison from completed benchmark evidence."""
# /// script
# dependencies = ["markdown-it-py==3.0.0"]
# ///
import html
import json
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/glm53-h200-comparison"
BASELINE = ROOT / "reports/glm53-superagent/full-20261121T033400Z/stream-metrics.jsonl"


def summaries(path):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    result = {r["concurrency"]: r for r in rows if r.get("type") == "summary"}
    if set(result) != {1, 2}:
        raise ValueError(f"Incomplete concurrency groups: {path}")
    for c, summary in result.items():
        requests = [r for r in rows if r.get("type") != "summary"
                    and not r.get("warmup") and r["concurrency"] == c]
        if len(requests) != summary["requests"]:
            raise ValueError(f"Request count mismatch: {path}, concurrency {c}")
        summary["mean_output_tokens"] = sum(
            r["usage"].get("completion_tokens", 0) for r in requests
        ) / len(requests)
    return result


def main():
    b200 = summaries(BASELINE)
    h200 = summaries(REPORT / "stream-metrics.jsonl")
    groups = [b200[1], b200[2], h200[1], h200[2]]
    metrics = [
        ("正常正文完成请求", lambda s: f'{s["useful_completions"]}/{s["requests"]}'),
        ("错误 / 截断", lambda s: f'{s["errors"]} / {s["truncated"]}'),
        ("TTFT 均值（秒）", lambda s: f'{s["ttft_s"]["mean"]:.3f}'),
        ("首次可见正文均值（秒）", lambda s: f'{s["first_visible_s"]["mean"]:.3f}'),
        ("E2E 均值（秒）", lambda s: f'{s["e2e_s"]["mean"]:.3f}'),
        ("E2E p95（秒）", lambda s: f'{s["e2e_s"]["p95"]:.3f}'),
        ("估算 TPOT 均值（毫秒）", lambda s: f'{s["approx_tpot_s"]["mean"] * 1000:.3f}'),
        ("平均输出 tokens / 请求", lambda s: f'{s["mean_output_tokens"]:.1f}'),
        ("聚合输出 tokens/s", lambda s: f'{s["output_tokens_per_s"]:.1f}'),
    ]
    table = [
        "| 指标 | B200 并发 1 | B200 并发 2 | H200 并发 1 | H200 并发 2 |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, value in metrics:
        table.append("| " + " | ".join([label] + [value(s) for s in groups]) + " |")
    comparison = {}
    for c in (1, 2):
        comparison[c] = {
            "h200_to_b200_throughput": h200[c]["output_tokens_per_s"] / b200[c]["output_tokens_per_s"],
            "h200_to_b200_mean_e2e": h200[c]["e2e_s"]["mean"] / b200[c]["e2e_s"]["mean"],
            "h200_to_b200_mean_tpot": h200[c]["approx_tpot_s"]["mean"] / b200[c]["approx_tpot_s"]["mean"],
        }
    (REPORT / "comparison.json").write_text(json.dumps(
        {"b200": b200, "h200": h200, "ratios": comparison}, ensure_ascii=False, indent=2
    ) + "\n")
    readme = REPORT / "README.md"
    text = readme.read_text()
    start = text.index("| 指标 |")
    end = text.index("\n\n", start)
    text = text[:start] + "\n".join(table) + text[end:]
    readme.write_text(text)
    body = MarkdownIt("commonmark", {"html": False}).enable("table").render(text)
    title = html.escape("GLM-5.3 · H200 与 B200 对照测试")
    document = f"""<!doctype html>
<html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
body{{font:16px/1.8 system-ui,sans-serif;color:#172d43;background:#edf2f6;margin:0}}
main{{max-width:1100px;margin:24px auto;padding:32px;background:white;border-radius:12px}}
h1{{color:#132f46}}h2{{border-bottom:1px solid #dbe5ed}}
table{{display:block;overflow:auto;border-collapse:collapse;font-size:14px}}
th,td{{padding:10px;border:1px solid #dbe5ed;white-space:nowrap}}
th{{background:#eaf2f6}}code{{overflow-wrap:anywhere}}a{{color:#096770}}
@media(max-width:650px){{main{{margin:8px;padding:18px}}}}
</style><main>{body}</main></html>"""
    (REPORT / "index.html").write_text(document)


if __name__ == "__main__":
    main()
