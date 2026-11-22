# AgentcoreShell 自部署 GLM-5.3 扫描复核

扫描已完成：2026-11-20 05:55:40–06:00:16 UTC，耗时约 4 分 36 秒。
目标提交：`3b4cc2689a1ed1d98383b0b7efdbe99fa8ea3845`。
Strix 运行 `agentcoreshell_bc7c`，状态 `completed`，退出码 2 表示发现问题。
共 41 次模型请求，3,065,228 输入 token、28,121 输出 token。

## 模型与修复

实际使用 Mumbai Spot `p6-b200.48xlarge` 的 8 张 NVIDIA B200，
通过 SGLang 加载 `zai-org/GLM-5.3`，checkpoint revision
`ba32f8c19c8738e2c57c71798c601d477a7bf844`。
这是 EC2 自部署推理；模型列表、GPU、镜像及函数调用往返验证分别保存在
[inference-verification.json](inference-verification.json) 和
[server-evidence.json](server-evidence.json)。
未配置 Bedrock Guardrails；这不意味着模型自身的安全行为全部关闭。

已修复 AMI 自带 Docker 与安装包冲突、NVMe 别名导致数据盘识别失败、
以及首次扫描 18 轮上限导致中止的问题。重试使用 60 轮上限并正常结束。

## 复核结论

发现 1 项有条件的 Shell 注入风险：`coding_workflow.py` 将 `task`
及其派生分支名直接插入嵌套 Shell 命令（81、83、86、89 行）。
独立无害验证使用模拟 AWS 客户端和假 git 命令：正常输入未创建标记，
注入输入成功创建标记；验证没有调用云端 API 或真实 git。
见 [task-injection-verification.json](task-injection-verification.json)。

**当前提交的输入仅来自操作者命令行 `sys.argv[1]`。未证实远程攻击者
能够控制该参数，因此不能把它认定为已确认的远程高危漏洞。**
当前按低风险加固项处理；若未来连接不可信工单、Webhook 或其他外部输入，
或操作者直接转交攻击者提供的任务文本，可能产生任意命令执行。

原始 Strix 报告标为 HIGH / CVSS 7.8，但其正文也承认当前发布形态风险低。
该分级依赖尚未实现的外部输入路径，故本复核不采纳其无条件高危结论。
原始报告保留在 [strix-report.md](strix-report.md)，便于追溯。

建议对工单标识使用严格允许列表；若必须支持任意文本，应尽量使用参数数组，
避免 Shell 解析。保留嵌套 `bash -c` 时，需要分别正确引用各个参数和整个内层命令，
不能只在外层随意加引号。目标仓库源码未在本次部署修复中修改。

## 范围与限制

扫描覆盖仓库 7 个文件及 8 个记录的检查面。覆盖记录存在 1 项缺口：
验证代理没有独立记录覆盖信息，根代理已有记录。
这是源码审计和本地模拟复现，没有验证已部署 AgentCore runtime 的实际 IAM、
网络或隔离配置，也没有完成依赖漏洞数据库扫描。没有发现不等于不存在其他问题。

运行证据见 [run.json](run.json)、[coverage.json](coverage.json)。
实例清理状态见 [final-cleanup.json](final-cleanup.json)。扫描结束后已提交终止及
强制终止请求，取消 Spot 请求，并删除临时 IAM 角色和实例配置文件。
清理监测进程会等待实例终止、确认两块 EBS 卷删除，再删除临时安全组；
只有该文件的 `complete` 为 `true` 才表示资源回收完成。
模型请求计价配置为零仅表示未使用收费模型 API；EC2 和存储仍产生费用。
