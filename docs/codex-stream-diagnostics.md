# Codex 响应流中断排查

检查日期：2026-11-23 UTC。状态：**尚未确认根因，尚未修复服务端或客户端断流**。

## 错误的含义

`stream disconnected before completion: stream closed before response.completed`
表示 Codex 尚未收到响应完成事件，连接就结束了。仅凭这条消息无法判断是模型服务、网络代理还是客户端导致。

本次 Codex 使用原生 `amazon-bedrock-runtime` provider 和
`us.openai.gpt-6-astra`；这条对话链路与 Strix 调用自建 GLM-5.3 的链路不同。
不能据此认定 GLM 推理失败，也不能据此认定 Strix 仍在后台运行。

## 已核实的证据

- CLI 和托管 app-server 版本均为 `0.171.0`。
- 本地 SQLite 日志在 2026-11-20 03:43:43 UTC 记录了相同错误，并进入
  第 1/5 次自动重试。这是历史记录，不能作为本次中断的直接原因。
- 日志另有 2026-11-21 的 WebSocket connection reset 记录。它属于客户端
  app-server 传输层，目前没有证据将其与本次模型响应流中断关联。
- 早期进程检查时深入复测尚未启动；随后批次已于 2026-11-23 10:58 UTC 完成。
  见[深入复测结果](../reports/h200-deep-followup-20261123T095202Z/README.md)。扫描完成不代表对话断流问题已修复。

## 配置验证

使用不会启动第二个服务的配置检查命令：

```sh
codex app-server --strict-config --print-startup-config
```

原配置退出码为 0。分别通过 `-c` 临时覆盖下列设置，检查均失败：

```text
model_providers.amazon-bedrock-runtime.stream_max_retries=10
model_providers.amazon-bedrock-runtime.stream_idle_timeout_ms=600000
model_providers.amazon-bedrock-runtime.request_max_retries=8
model_providers.amazon-bedrock-runtime.aws.stream_max_retries=10
```

错误为 `startup configuration unavailable`。这些覆盖没有写入配置文件。
特别注意：不加 `--strict-config` 时，放在 `.aws` 下的未知参数可能通过
启动检查；这不能证明参数有效。

[官方通用配置参考](https://developers.openai.com/codex/config-reference/)
列有 `stream_max_retries`、`stream_idle_timeout_ms` 和
`request_max_retries`，但本机版本的原生 Bedrock provider 未通过上述校验。
因此不能将添加这些参数作为本环境已验证的修复。

## 后续定位需要的证据

下一次错误需要关联发生时间、thread/turn ID、模型请求 ID，以及同一时段
provider 的 WARN/ERROR。日志位于 `~/.codex/logs_2.sqlite` 和
`~/.codex/app-server-daemon/daemon.stderr.log`。分享时仅提取相关错误，
避免公开完整 SDK trace、凭据或会话内容。

真正的修复需要根据相关证据定位客户端、代理或 Bedrock 上游，并在修改后
验证完整响应事件。增加超时不会修复对端主动关闭连接的问题。

长时间扫描应独立启动、持久化 PID/进度/结果，并在重连后核对进程；
这种做法只能降低对话断流对任务执行的影响，不能消除本错误。
