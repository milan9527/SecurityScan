# GLM-5.3 自建推理与 Strix 仓库测试（2026-11-20）

## 测试对象与环境

- 仓库：`https://github.com/milan9527/agentcore-superagent-update`，提交 `0a20b8b14ab9abdf7301ec1e475be2d6dc2effde`，本地约 56 MB。
- 模型：`zai-org/GLM-5.3`，revision `ba32f8c19c8738e2c57c71798c601d477a7bf844`。本轮为 EC2 自建 SGLang 推理，非 Bedrock 托管调用。
- GPU：`p6-b200.48xlarge`，8×B200，`ap-south-1a`，持久型 Spot `i-0b33a1d2ee1a2065f`。
- SGLang 镜像：`lmsysorg/sglang@sha256:f832b5c39559c9caa900b22ad37c76fcce66470676855c42052102c537812f1f`。
- 配置：TP=8、FP8 KV cache、context=262144、max-running-requests=2、mem-fraction-static=0.85、chunked-prefill-size=32768；关闭异步权重加载使启动成功，但尚未证明其故障根因。
- 模型识别与工具调用证据：[inference-verification.json](inference-verification.json)。

## Strix 执行结果

四个场景均记录 `scan_completed=true`，共 770 次模型请求记录成功。退出码均为 2；完成状态依据扫描产物判断，而非将其当作退出码 0。原始发现含重复项，不能等同于已确认漏洞数。

| 场景 | 用时（秒） | 请求数 | 请求延迟 p50 / p95（秒） | 原始发现数 |
|---|---:|---:|---:|---:|
| 认证与授权 | 372 | 175 | 1.904 / 11.088 | 13 |
| 路径与文件 | 752 | 242 | 2.082 / 15.440 | 5 |
| Webhook | 417 | 153 | 1.794 / 8.260 | 3 |
| 工具与执行 | 414 | 200 | 2.094 / 12.687 | 11 |

这些请求使用非流式调用，因此没有可用于计算 TTFT 的事件。扫描耗时包括代理及工具运行，不能当作单次推理 TTOT。

发布证据：[扫描汇总](scan-summary.json)。汇总省略逐请求 usage 和本地原始报告路径；完整扫描日志、模型生成的未核验报告及目标源码保留在本地。

## 独立核验

1. **WebSocket 订阅缺少鉴权：隔离本地复现。** 使用仓库原始 `execution.gateway.ts`，不发送凭证，订阅已知的合成 executionId 后收到合成工作流事件。网关注册和订阅逻辑没有验证身份及执行所有权。实际部署风险还取决于外层入口鉴权、executionId 可获得性等条件。建议在握手认证，并在每次订阅时验证执行记录所属用户/租户。
   - [复现代码](validation/websocket-local-proof.ts)、[结果](validation/websocket-local-proof.json)。未访问真实用户数据，也未测试公网部署。
2. **Python ZIP 路径穿越：本地证据与扫描结论矛盾。** 对 `python -m zipfile -e` 构造 `../marker.txt`，Python 3.9.25 将路径规范化在提取目录内，目录外文件不存在。原始工具场景 vuln-0005 的复现主张不能采信；尚未测试生产 Python 版本或其他解压分支。
   - [结果](validation/zipfile-traversal.json)、[解释器实现](validation/zipfile-extract-member-source.txt)。

其余发现未完成独立验证。模型生成的 PoC 描述及 CVE 编号均应逐项核验，不宜直接作为可利用漏洞发布。

## 流式性能测试方法

另用四份实际源码包做只读审计请求，分别覆盖认证、路径、Webhook、工具，输入约 9399 / 27662 / 11281 / 17698 tokens。每个场景在并发 1 和 2 下各重复 5 次，共 40 次正式请求，另有一次排除统计的预热。

- 输出预算 32768 tokens，reasoning_effort=low，temperature=0。该预算与推理档位降低了先前 8192/high 配置中思考耗尽输出预算的风险；由于输入也发生变化，不能将差异归因于单个参数。
- TTFT：首个内容、思考或工具增量；首次可见正文另记 first_visible_s。
- TTOT：请求开始至最后生成增量；e2e 包含终止事件接收。
- TPOT：以生成 token 数估算；SSE 分块并非逐 token，结果是近似值。
- 指标由客户端经过 SSM 隧道测量，包含网络及隧道开销。重复输入可能命中缓存；未控制冷缓存。
- 每个并发档只有 20 个样本，p95 为插值估计。非 InferenceX 同协议实验，不能直接用于与其排名比较。
- `useful_completion` 只表示存在正文、正常 stop 且无协议错误，不代表审计结论正确。

## 流式性能结果

40/40 次正式请求均正常结束并产生正文；错误、截断和仅思考无正文均为 0。

| 并发 | 请求数 | TTFT p50 / p95（秒） | 首次正文 p50 / p95（秒） | TTOT p50 / p95（秒） | 聚合输出 tokens/s |
|---|---:|---:|---:|---:|---:|
| 1 | 20 | 0.353 / 1.019 | 7.131 / 15.504 | 18.809 / 31.808 | 127.19 |
| 2 | 20 | 0.339 / 0.400 | 7.330 / 18.137 | 19.125 / 37.264 | 236.18 |

并发 1 / 2 的 e2e p50 分别为 18.819 / 19.135 秒；近似 TPOT p50 分别为 7.641 / 8.094 毫秒。吞吐量为该批所有输出 tokens 除以批次墙钟时间，包含思考 tokens，不能当作每请求正文生成速度。

请求指标和汇总：[stream-metrics.jsonl](stream-metrics.jsonl)、[stream-summary.json](stream-summary.json)。发布的请求指标仅移除模型回答正文，保留预热标记、时序和 token 用量；统计排除预热。此次样本证明 32768 输出预算与 low 推理配置下能够完成这些源码审计请求，不能保证更大任务永不耗尽预算。Strix 上下文与输出预算覆盖参数的相关测试此前已通过（22 项）。

## Codex 对话断流

`stream closed before response.completed` **仍未证实修复**。这是 Codex 到其模型提供方的连接，与本轮自建 GLM 推理链路不同。后台扫描完成不代表对话流故障解决。已保留请求 ID、时间和配置限制：[故障记录](stream-incident-20261120.md)。需要服务端按请求 ID 关联调查，现有证据不足以确定断开连接的具体环节。

## 资源收尾

40 次正式流式测试结束且结果落盘后，已调用 `StopInstances`。截至 2026-11-20T15:04:14.714760+00:00，`DescribeInstances` 已确认实例为 **stopped**。未执行 terminate，未取消持久型 Spot。两块 EBS（200 GB 根盘和 2048 GB 模型缓存盘）保留，DeleteOnTermination=false，仍产生存储费用。最新观察见 [resource-status.json](resource-status.json)。
