# /// script
# requires-python = ">=3.9"
# dependencies = ["markdown-it-py==3.0.0"]
# ///
"""Generate the standalone HTML report: uv run scripts/render_report.py."""
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/glm53-superagent"


def main():
    body = MarkdownIt("commonmark", {"html": False}).enable("table").render(
        (REPORT / "RESULTS.md").read_text(encoding="utf-8")
    )
    # Evidence links remain usable when only this HTML file is downloaded.
    from urllib.parse import urljoin
    import re
    base = "https://github.com/milan9527/SecurityScan/blob/main/reports/glm53-superagent/"
    body = re.sub(r'href="([^"]+)"',
                  lambda m: 'href="' + urljoin(base, m.group(1)) + '"', body)
    document = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="GLM-5.3 自建推理、Strix 仓库审计及流式性能实测，包含独立核验和方法限制。">
<title>GLM-5.3 × Strix · 测试报告</title>
<style>
:root{color-scheme:light;--ink:#172d43;--muted:#53697c;--line:#dbe5ed;--accent:#096770}
*{box-sizing:border-box}
body{margin:0;background:#edf2f6;color:var(--ink);font:16px/1.8 system-ui,-apple-system,"Segoe UI",sans-serif}
header{background:#132f46;color:white;padding:44px max(24px,calc((100% - 1040px)/2))}
header p{margin:5px 0;color:#cfdee9}header strong{font-size:30px;letter-spacing:.02em}
main{max-width:1100px;margin:24px auto;background:white;border:1px solid var(--line);border-radius:14px;padding:36px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:30px}
.card{border-top:4px solid var(--accent);background:#f0f7f8;padding:18px;border-radius:6px}
.card b{display:block;font-size:28px}.card span{color:var(--muted)}
h1{font-size:27px;line-height:1.45}h2{font-size:22px;margin-top:38px;border-bottom:1px solid var(--line);padding-bottom:8px}
a{color:var(--accent);text-underline-offset:3px;overflow-wrap:anywhere}
code{font-size:.88em;background:#f1f4f7;border-radius:3px;padding:2px 4px;overflow-wrap:anywhere}
table{display:block;overflow-x:auto;border-collapse:collapse;width:100%;font-size:14px;margin:20px 0}
th,td{padding:12px;border:1px solid var(--line);white-space:nowrap}th{background:#eaf2f6;text-align:left}
li{margin:9px 0}footer{max-width:1040px;margin:24px auto;padding:0 20px 32px;color:var(--muted)}
@media(max-width:650px){main{margin:12px;padding:20px}.cards{grid-template-columns:1fr}header{padding:28px 24px}}
@media print{body{background:white;font-size:11pt}header{padding:15px;color:black;background:white}header p{color:#444}main{border:0;margin:0;padding:0}table{display:table;font-size:9pt}th,td{white-space:normal;padding:6px}h2{break-after:avoid}.card{break-inside:avoid}footer{padding:0}}
</style>
</head>
<body>
<header><p>SECURITYSCAN · 2026-11-20</p><strong>GLM-5.3 × Strix</strong>
<p>EC2 自建模型 · 仓库审计 · 流式推理实测</p></header>
<main>
<div class="cards" aria-label="测试摘要">
<div class="card"><b>4 场景 / 770 请求</b><span>32 条原始发现，尚未全部核验</span></div>
<div class="card"><b>40 / 40</b><span>流式审计请求正常结束并产生正文</span></div>
<div class="card"><b>0.339 秒</b><span>并发 2 TTFT p50；首次正文 7.330 秒</span></div>
</div>
""" + body + """
</main>
<footer>从 RESULTS.md 自动生成。证据链接指向 GitHub；阅读本文无需外部脚本或样式。
浏览器打印可导出 PDF。上述完成率不证明发现准确，Codex 对话断流仍待调查。</footer>
</body></html>
"""
    (REPORT / "index.html").write_text(document, encoding="utf-8")
    print("Generated reports/glm53-superagent/index.html")


if __name__ == "__main__":
    main()
