# SecurityScan

GLM-5.3 与 Strix 的安全测试、漏洞核验和推理性能记录，包含 Bedrock Flex 靶场测试与 EC2 自建模型的大型仓库审计。

## 最新测试结论（2026-11-21）

**完整 Strix deep 扫描已完成，用时 704 秒（11 分 44 秒）；637/637 次模型请求成功，611 次工具调用。** 单次模型请求平均延迟为 **4.001 秒**。生成 **29 条待独立核验发现**：Critical 6、High 6、Medium 12、Low 4、Info 1。退出码 2 表示发现达到 fail-on 阈值；产物状态为 `completed`，不是模型调用失败。

目标为 `agentcore-superagent-update` 的固定提交 `0a20b8b14ab9abdf7301ec1e475be2d6dc2effde`。完成时间为 **2026-11-21 04:15 UTC**，运行 ID 为 `agentcore-superagent-update_e35b`。704 秒不包含模型加载（本次约 25 分钟）。发现尚未逐项核验，也不能与历史 32 条直接相加为独立漏洞数。

### 本轮测试部署架构

![GLM-5.3 与 Strix 部署架构](reports/glm53-superagent/assets/deployment-architecture.svg)

SGLang 0.5.23 自建服务启用 MTP（EAGLE，steps=3、top-k=1、draft tokens=4），TP=8、FP8 KV cache、context=262144、并行请求上限 2。控制主机通过 SSM 将本机 18000 转发到 GPU 8000；后台 systemd 服务将进度和证据落盘。本轮测试时 GPU 保持运行，自动停止已禁用；[资源记录](reports/glm53-superagent/resource-status.json)中的 `running` 是带时间戳的观察值。

### 最新独立流式性能（MTP，经过 SSM）

| 并发 | 成功请求 | TTFT 均值 / P95（秒） | 首次正文均值（秒） | TTOT 均值 / P95（秒） | E2E 均值（秒） | 估算 TPOT 均值（毫秒） | 聚合输出 tokens/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 12/12 | 0.325 / 0.372 | 4.353 | 10.213 / 18.178 | 10.220 | 3.653 | 263.3 |
| 2 | 12/12 | 0.337 / 0.423 | 4.973 | 11.105 / 17.317 | 11.111 | 4.209 | 447.5 |

认证、路径、Webhook、工具四类源码审计，每类每并发重复 3 次，输出预算 8192、reasoning=low；24 次请求均无错误、截断或仅思考输出。并发 2 提高聚合吞吐，但单请求平均 TTOT 略增。TTFT 取首个非空 reasoning/content/tool 增量，首次正文单列；TTOT 截止最后生成增量，E2E 截止流结束。吞吐包含思考 tokens。

**完整 Strix 扫描采用非流式请求，没有 TTFT 测量；上表是独立基准，不能当作完整扫描指标。** 每档仅 12 个样本，P95 仅供参考；与历史实验及 InferenceX 的预算、缓存、硬件和负载不一致，不能直接排名或据此计算 MTP 加速比。Codex 对话断流仍未证实修复。

证据：[完整扫描摘要](reports/glm53-superagent/full-20261121T033400Z/README.md)、[结构化汇总](reports/glm53-superagent/full-20261121T033400Z/progress-summary.json)、[流式指标](reports/glm53-superagent/full-20261121T033400Z/stream-metrics-public.jsonl)。

### 补充完整扫描（2026-11-21）

| 场景 | 扫描耗时（秒） | 成功模型请求 | 工具调用 | 请求平均 / P95（秒） | 待核验发现 |
|---|---:|---:|---:|---:|---:|
| AgentcoreShell deep | 120 | 66/66 | 66 | 1.829 / 4.511 | 1 |
| Superagent 前端与部署 | 781 | 575/575 | 559 | 2.847 / 8.985 | 28 |

两次扫描均完成，采用自建 GLM-5.3、TP8 和 MTP，顺序执行。请求延迟来自非流式调用，不代表 TTFT 或流式 TTOT；发现尚未独立核验，不与其他扫描相加为独立漏洞总数。详见[补充扫描摘要](reports/glm53-additional-full/20261121T095600Z/README.md)。

## 历史测试结论摘要（2026-11-20）

- **Bedrock Flex 本地靶场**：SQLite 登录 SQL 注入已复现，5 组输入均绕过有漏洞函数；参数化查询阻止全部 5 组绕过。
- **EC2 自建模型仓库审计**：使用 `zai-org/GLM-5.3`、SGLang、`p6-b200.48xlarge`（8×B200，ap-south-1 Spot），扫描 [agentcore-superagent-update](https://github.com/milan9527/agentcore-superagent-update/tree/0a20b8b14ab9abdf7301ec1e475be2d6dc2effde)。本轮不是 Bedrock 托管调用。
- **四个 Strix 场景完成**：认证、路径、Webhook、工具，共 770 次成功模型请求，产生 **32 条原始待核验发现**，含重复项。四次退出码均为 2，完成依据是扫描产物的 `scan_completed=true`。
- **核验结果**：WebSocket 未鉴权订阅在原始网关的隔离本地环境复现，仅使用已知合成 ID 和事件；没有证明公网部署可利用。ZIP 路径穿越在 Python 3.9.25 测试分支未复现，与模型报告主张矛盾。其余发现仍待独立验证。
- **输出预算与稳定性**：独立流式源码审计采用 32768 输出预算、low reasoning，40/40 请求正常结束且有正文，无错误、截断或仅思考输出；这不代表漏洞结论正确，也不保证更大任务永不耗尽预算。
- **对话断流仍未证实修复**：Codex 的 `stream closed before response.completed` 与自建 GLM 链路不同，不能用上述 40 次成功请求宣称修复。
- **历史资源收尾**：AWS 已确认 GPU 实例 `stopped`，两块 EBS 保留并继续产生存储费用。

### 新增独立对照：精简输出与 MTP

三组共 120/120 次正式请求完成，无错误或截断。下表为 GPU localhost 实测，每格 20 次；两项优化分别与同一新基线比较。

| 并发 | 基线 TTOT 均值 | 精简输出 TTOT 均值 | MTP TTOT 均值 | MTP TPOT 降幅 |
|---|---:|---:|---:|---:|
| 1 | 19.65 秒 | 15.77 秒（−19.7%） | 8.64 秒（−56.0%） | 57.6% |
| 2 | 19.63 秒 | 17.24 秒（−12.2%） | 9.89 秒（−49.6%） | 53.2% |

MTP 明显加速生成，但并发 2 TTFT p95 从 0.115 秒升至 0.930 秒。精简指令主要减少思考 tokens，正文字符数反而增加约 35%–37%。抽查 24 份回答仍发现错误和前提遗漏，不能声称质量无损。本轮为源码审计推理对照，没有测完整 Strix 工具循环的加速比。详见 [实验协议](reports/glm53-superagent/ABLATION-PROTOCOL.md) 与 [质量核验](reports/glm53-superagent/ABLATION-QUALITY.md)。该历史实验完成后 GPU 曾停止；2026-11-21 本轮测试时已重新启动并保持运行。

### 历史流式测试（SSM 隧道）

| 并发 | 正式请求 | TTFT p50 / p95（秒） | 首次正文 p50 / p95（秒） | TTOT p50 / p95（秒） | 聚合输出 tokens/s |
|---|---:|---:|---:|---:|---:|
| 1 | 20 | 0.353 / 1.019 | 7.131 / 15.504 | 18.809 / 31.808 | 127.19 |
| 2 | 20 | 0.339 / 0.400 | 7.330 / 18.137 | 19.125 / 37.264 | 236.18 |

TTFT 包含首个思考/内容/工具增量；首次正文单列。吞吐量包含思考 tokens，按批次总输出除以墙钟时间计算。测试经过 SSM 隧道，重复输入可能命中缓存，每个并发档仅 20 个样本；与 InferenceX 协议不同，不能直接比较排名。Strix 非流式扫描未测 TTFT，上表来自另外的只读源码审计请求。

完整环境、指标定义、限制与证据见 [详细测试报告](reports/glm53-superagent/RESULTS.md)；[HTML 报告](reports/glm53-superagent/index.html) 可下载后在浏览器打开（GitHub 文件页通常显示源码，未配置 Pages）。

HTML 与 Markdown 共用报告源，重新生成：

```bash
uv run scripts/render_report.py
```

## 早期 Bedrock Flex 靶场测试

### 复现验证（不调用模型）

```bash
PYTHONPATH="$PWD/strix-fixture" python3 strix_sqli_poc.py
```

### 重新扫描

需要 Git、uv、Docker、GNU timeout，以及拥有 Bedrock 模型调用权限的 AWS 身份。Strix 源码固定为上游提交 `a1ccf777d80e812edf23fc8b82bdc17def6143ac`，由 submodule 管理。

```bash
bash setup-strix.sh
bash run-strix-glm.sh
```

启动脚本使用 `us-east-1`、`bedrock/converse/us.zai.glm-5.3` 和 Flex tier；会产生 AWS 调用费用。Bedrock 参数适配保存在 `strix_bedrock_params.patch`，安装脚本会应用它。

### 测试记录

- [中文实测说明](strix_glm_report.md)
- [扫描报告](reports/strix-fixture_8f1e/penetration_test_report.md)
- [漏洞详情](reports/strix-fixture_8f1e/vulnerabilities/vuln-0001.md)
- [工具执行证据](strix_sqli_evidence.txt)
- [PoC 重放输出](strix_sqli_replay.txt)

未配置 Bedrock Guardrails；这不代表模型内置安全限制已关闭。本次结果只适用于该本地靶场。4096 token 输出上限曾造成子代理异常，根代理接手后完成测试，详见实测说明。

本地虚拟环境、原始会话数据库及运行日志不提交。上游 Strix 的源码及许可证见 `strix-src` 子模块。
