# Strix + Bedrock GLM-5.3 实测

运行完成：2026-11-20 02:17:29–02:28:10 UTC，约 10 分 41 秒。
Strix `run.json` 状态为 `completed`，产生 1 个已确认漏洞。

## 配置

- Strix 1.7.1，源码提交 `a1ccf777d80e812edf23fc8b82bdc17def6143ac`。
- LiteLLM 模型：`bedrock/converse/us.zai.glm-5.3`，区域 `us-east-1`。
- 请求 Flex tier；独立连通性请求的响应 `service_tier` 为 `flex`。
- 未配置 Bedrock Guardrails。使用环境 AWS 身份认证。
- 本地适配 `max_tokens`、`service_tier` 到 LiteLLM 顶层参数，补丁见 `strix_bedrock_params.patch`。
- 本次实际配置：输出上限 4096、max-turns 12、预算上限 $2、900 秒超时。

## 结果与边界

测试对象是本次创建的本地内存 SQLite 靶场，不是外部网站。
Strix 通过工具执行 Python，验证有漏洞的 `login()` 对 5 组注入输入全部返回 True；
参数化查询 `login_parameterized()` 对同样 5 组输入全部返回 False。
有效密码、错误密码、不存在用户三组普通登录对照均符合预期。
保存的 PoC 在宿主机重放也成功，退出码为 0。

Strix 报告为 CWE-89、Medium、CVSS 5.1；该评级针对本地靶场。
此函数返回布尔值，未测试实际 Web 会话或生产账号接管，不能据此推断生产影响。

验证子代理异常退出，根代理接手并再次执行 PoC，最终完成漏洞登记与扫描报告。
日志出现多次 `finish=length`：4096 token 上限导致部分响应截断、额外恢复轮次；
本次最终成功，不代表此配置已经适合稳定的长任务。
本次未调整上限或另行重跑扫描。

Strix 显示约 3.3M 输入 token（其中约 3.2M 缓存）、94.2K 输出 token；
显示成本约 $0.9834，仅为工具估算，未经 AWS 账单核对。

本次证明 GLM-5.3 可以在 Strix 中调用工具并完成这一 SQL 注入靶场测试。
未测试或证明“关闭模型安全限制”，也不能据此判断任意渗透测试任务的拒绝率。

## 文件与复现

- 原始报告：`reports/strix-fixture_8f1e/penetration_test_report.md`
- 漏洞详情：`reports/strix-fixture_8f1e/vulnerabilities/vuln-0001.md`
- 原始工具执行证据：`strix_sqli_evidence.txt`
- 恢复自工具执行记录的 PoC：`strix_sqli_poc.py`
- 宿主机重放输出：`strix_sqli_replay.txt`
- 启动脚本：`run-strix-glm.sh`

在本目录重放 PoC（无需调用模型）：

```bash
PYTHONPATH="$PWD/strix-fixture" python3 strix_sqli_poc.py
```

重新发起扫描（会调用 Bedrock 并计费）：

```bash
bash run-strix-glm.sh
```
