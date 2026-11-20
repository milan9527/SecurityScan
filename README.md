# SecurityScan

GLM-5.3 与 Strix 的安全测试、漏洞核验和推理性能记录，包含 Bedrock Flex 靶场测试与 EC2 自建模型的大型仓库审计。

## 测试结论摘要（2026-11-20）

- **Bedrock Flex 本地靶场**：SQLite 登录 SQL 注入已复现，5 组输入均绕过有漏洞函数；参数化查询阻止全部 5 组绕过。
- **EC2 自建模型仓库审计**：使用 `zai-org/GLM-5.3`、SGLang、`p6-b200.48xlarge`（8×B200，ap-south-1 Spot），扫描 [agentcore-superagent-update](https://github.com/milan9527/agentcore-superagent-update/tree/0a20b8b14ab9abdf7301ec1e475be2d6dc2effde)。本轮不是 Bedrock 托管调用。
- **四个 Strix 场景完成**：认证、路径、Webhook、工具，共 770 次成功模型请求，产生 **32 条原始待核验发现**，含重复项。四次退出码均为 2，完成依据是扫描产物的 `scan_completed=true`。
- **核验结果**：WebSocket 未鉴权订阅在原始网关的隔离本地环境复现，仅使用已知合成 ID 和事件；没有证明公网部署可利用。ZIP 路径穿越在 Python 3.9.25 测试分支未复现，与模型报告主张矛盾。其余发现仍待独立验证。
- **输出预算与稳定性**：独立流式源码审计采用 32768 输出预算、low reasoning，40/40 请求正常结束且有正文，无错误、截断或仅思考输出；这不代表漏洞结论正确，也不保证更大任务永不耗尽预算。
- **对话断流仍未证实修复**：Codex 的 `stream closed before response.completed` 与自建 GLM 链路不同，不能用上述 40 次成功请求宣称修复。
- **资源已停止**：AWS 已确认 GPU 实例 `stopped`，两块 EBS 保留并继续产生存储费用。

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
