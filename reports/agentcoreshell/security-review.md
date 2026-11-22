# AgentcoreShell 源代码安全审计

- 仓库：https://github.com/milan9527/AgentcoreShell
- 提交：`3b4cc2689a1ed1d98383b0b7efdbe99fa8ea3845`
- 日期：2026-11-20
- 范围：全部七个已跟踪文件，快速全仓库审计及本地无害复现。
- 引擎：Strix，`bedrock/converse/us.zai.glm-5.3`，区域 `us-east-1`，配置请求 `service_tier=flex`。成功的 Bedrock HTTP 200 请求可证实模型调用；实际计费层级未独立核对。

## 已复现：任务编号未经转义拼接到 Shell 命令（CWE-78，条件性风险）

位置：`coding_workflow.py:81、83、86、89`；当前入口为 `coding_workflow.py:103` 的命令行参数。

`task` 被直接拼入 Git 分支名和提交说明，再交给 Bash 解析。例如任务编号 `JIRA-1234; printf verified > injection_marker #` 会让 checkout 命令执行额外的 `printf`。如果以后把工单字段、Webhook 参数或其他用户输入传给此函数，输入方可能获得运行环境内的命令执行能力，影响范围取决于该环境可访问的文件、凭据和网络。

当前仓库只展示操作者传入 CLI 参数；未发现未认证远程入口，也没有证据证明攻击者能控制该参数。因此不将其评为已成立的未认证远程代码执行。对不可信输入的自动化集成，应在上线前修复。

验证：使用假的 AgentCore 客户端和 Git 程序，仅在自动清理的临时目录中重放生成的 Bash 命令。正常任务编号未创建文件；含分隔符的任务编号成功创建内容为 `verified` 的标记文件。该独立复现没有调用目标 AWS runtime，也没有真实 Git 操作。Strix 另在临时本地仓库与本地 bare remote 中验证了 Git 提交和推送行为；未向 GitHub 或目标服务推送。

证据：`task_injection_evidence.json`；可重现脚本：`verify_task_injection.py`。

```bash
python reports/agentcoreshell/verify_task_injection.py /home/ec2-user/bedrock/AgentcoreShell
```

修复建议：根据业务规则对任务编号做严格白名单校验，例如完整匹配 `[A-Za-z][A-Za-z0-9]*-[0-9]+`。尽可能通过结构化参数传递 Git 参数；必须使用 Shell 时，对各参数及外层脚本分别正确转义，避免把 `shlex.quote` 的结果再次嵌入未处理的双引号层。任何 Git 步骤失败时停止后续操作。

## 其他审计观察

- 安装、lint、Git 操作的失败处理不完整，可能继续执行或错误显示推送成功；属于流程可靠性和发布控制问题。
- `npm install` 会运行依赖脚本，测试输出会进入模型提示，工作流可自动提交推送。若处理不可信仓库，应隔离执行环境、限制权限，并对推送设置审核；本次没有验证提示注入或供应链攻击成立。
- `shell_client.py` 和 `interactive.py` 的显式 Shell 执行属于产品预期功能，不能仅据此报告命令注入。
- 配置中的 AWS runtime ARN 和账号 ID 是资源标识符，不是密钥。
- 未运行目标 AWS runtime，未验证部署端 IAM、网络隔离、会话隔离或服务端鉴权；未对依赖做完整漏洞数据库比对。未发现其他已证实漏洞不代表这些边界安全。


## 最终扫描状态

Strix 已于 2026-11-20 03:06:58 UTC 完成（约 18 分钟），正式报告 1 项条件性命令注入，评级 Low / 3.7，无已确认的高危或严重问题。全部七个源文件已审阅；覆盖记录仍保留 1 项需跟进的运行时权限、供应链与提示反馈链路风险，扫描完成不表示该项已排除。

Strix 报告的本地验证为 24/24 断言通过，并验证了注入文件被自动提交到本地测试远端。其静态工具报告无新增发现；依赖没有锁文件，离线扫描的零结果不能证明部署依赖不存在已知漏洞。

- 原始扫描报告：`strix-report.md`。其中“trust-boundary violation”的表述须结合前述不可信输入前提理解；当前 CLI 未证明存在攻击者到操作者的权限跨越。
- 脱敏模型调用证据：`model-invocation-evidence.json`，仅包含调用元数据，不包含模型推理、提示或凭据。
- 本次保留目标源代码不变，未进行部署端渗透测试。
