#!/usr/bin/env python3
"""Durable sequential H200 source scans, with continuously updated reports."""
import argparse
import datetime
import html
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FOCUS = {
    "gitlab": "GitLab Rails platform: authentication and authorization, project/group "
    "boundaries, repository/archive/file handling, imports and webhooks, CI job trust boundaries.",
    "grafana": "Grafana Go/TypeScript platform: organization isolation and RBAC, "
    "datasource proxy SSRF, plugin routes, dashboard/share permissions, file handling.",
    "airflow": "Apache Airflow Python platform: API authentication and authorization, "
    "DAG/task/executor trust boundaries, connection/variable access, serialization, "
    "log and file endpoints. Distinguish explicitly trusted DAG authors from untrusted API users.",
}


def write_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def render(out, state):
    write_json(out / "progress.json", state)
    text = [
        "# H200 大型开源仓库 Strix 安全测试",
        "",
        "机型：p5en.48xlarge，8×NVIDIA H200，东京；自部署 GLM-5.3，Strix Agent 编排。",
        "范围：固定提交的本地源码及隔离沙箱验证，不测试项目公共服务。",
        "大型仓库扫描不保证穷尽所有代码路径；发现需独立复核。",
        "",
        f"批次状态：{state['status']}；更新时间：{state['updated_at']}",
        "",
        "| 仓库 | 文件数 | 固定提交 | 状态 |",
        "|---|---:|---|---|",
    ]
    for case in state["cases"]:
        text.append(f"| {case['name']} | {case['tracked_files']} | "
                    f"`{case['commit']}` | {case['status']} |")
    text += [
        "",
        "TTFT 为首个非空推理、正文或工具调用增量到达时间；另记录正文 TTFT。",
        "请求 E2E 包含网络、排队、prefill 和 decode；扫描 E2E 另包含工具执行。",
        "吞吐量使用全部 8 张卡的成功请求输出 tokens / 模型流量时间窗（含空闲间隔），"
        "不是单卡速度，也不是饱和基准。仅在 usage 完整时给出。",
        "",
        "| 仓库 | 成功流式请求 | TTFT p50 / p95（秒） | 请求 E2E p50 / p95（秒） | "
        "输出 tokens/s（流量时间窗） | 扫描 E2E（秒） | 待复核发现 |",
        "|---|---:|---|---|---:|---:|---:|",
    ]
    def pair(summary, key):
        d = summary.get(key)
        return "未测得" if not d else f"{d['p50']/1000:.3f} / {d['p95']/1000:.3f}"
    for case in state["cases"]:
        path = out / case["name"] / "performance-summary.json"
        if path.exists():
            s = json.loads(path.read_text())
            throughput = s.get("output_tokens_per_traffic_window_second")
            text.append(
                f"| {case['name']} | {s['successful_streams']} | {pair(s, 'ttft_ms')} | "
                f"{pair(s, 'request_e2e_ms')} | "
                f"{'未测得' if throughput is None else f'{throughput:.2f}'} | "
                f"{s['scan_status']['elapsed_s']} | "
                f"{s.get('strix', {}).get('unverified_findings', '未测得')} |"
            )
    text += ["", "各仓库子目录保留扫描日志、性能记录和 Strix 结果；超时或失败不得视为扫描通过。", ""]
    md = "\n".join(text)
    (out / "README.md").write_text(md)
    (out / "index.html").write_text(
        '<!doctype html><html lang="zh"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>H200 大型仓库安全测试</title>'
        '<style>body{max-width:1300px;margin:40px auto;padding:0 20px;font:16px/1.7 sans-serif}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
        '<h1>H200 大型仓库安全测试</h1><pre>' + html.escape(md) + "</pre></html>"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--instructions-dir", type=Path,
                        help="Use per-repository follow-up instructions instead of broad discovery")
    args = parser.parse_args()
    if args.instructions_dir:
        for name in FOCUS:
            if not (args.instructions_dir / f"{name}.txt").is_file():
                parser.error(f"Missing instructions for {name}")
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    if (args.out / "progress.json").exists():
        raise SystemExit("Use a fresh output directory to preserve previous evidence")
    state = {"status": "running", "cases": []}
    for name in FOCUS:
        target = (args.targets / name).resolve()
        files = subprocess.check_output(["git", "-C", str(target), "ls-files", "-z"]).split(b"\0")[:-1]
        state["cases"].append({
            "name": name, "target": str(target), "tracked_files": len(files),
            "commit": subprocess.check_output(
                ["git", "-C", str(target), "rev-parse", "HEAD"], text=True).strip(),
            "status": "queued",
        })
    def update():
        state["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        render(args.out, state)
    update()
    common = (HERE / "superagent/full.txt").read_text()
    for case in state["cases"]:
        case_out = args.out / case["name"]
        case_out.mkdir()
        instruction = case_out / "instructions.txt"
        instruction.write_text(
            (common + "\n\n" + (args.instructions_dir / f"{case['name']}.txt").read_text())
            if args.instructions_dir else
            common + "\n\nTarget-specific focus:\n" + FOCUS[case["name"]] +
            "\nThis is a large repository. Map major trust boundaries first, delegate "
            "at most four specialized agents, prioritize concrete reachable paths and "
            "report coverage gaps explicitly. Do not attempt exhaustive reading. "
            "Use minimal isolated reproductions; do not launch a full production stack. "
            "Do not scan any public host or use real secrets. Do not modify target source. "
            "Conclude with evidence-backed findings and honest limitations.\n"
        )
        env = dict(os.environ, STRIX_TARGET=case["target"],
                   STRIX_REPORT_DIR=str(case_out), STRIX_INSTRUCTION_FILE=str(instruction))
        case["status"] = "starting"
        update()
        with (case_out / "runner.log").open("w") as log:
            process = subprocess.Popen(["bash", str(HERE / "run-h200-scan.sh")],
                                       env=env, stdout=log, stderr=subprocess.STDOUT)
            case["pid"] = process.pid
            while process.poll() is None:
                phase = case_out / "phase.txt"
                case["status"] = phase.read_text().strip() if phase.exists() else "starting"
                update()
                time.sleep(20)
        case["exit_code"] = process.returncode
        summary = case_out / "performance-summary.json"
        complete = summary.exists() and json.loads(summary.read_text()).get("complete_scan")
        case["status"] = "completed" if complete else "incomplete"
        update()
    state["status"] = ("completed" if all(c["status"] == "completed" for c in state["cases"])
                       else "finished_with_incomplete_scans")
    update()


if __name__ == "__main__":
    main()
