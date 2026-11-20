# GLM-5.3 精简输出与 MTP 独立对照

实验日期：2026-11-20。本文记录实验设计；结果须以保存的请求记录为准。

## 实验矩阵

| 组别 | 提示词 | 推理服务 | 用途 |
|---|---|---|---|
| baseline | 原始审计提示词 | 不启用 speculative decoding | 两组共享的新基线 |
| concise | 基线追加紧凑表格输出要求 | 与 baseline 相同 | 单独检验精简输出 |
| mtp | 与 baseline 完全相同 | 启用 GLM NextN / EAGLE | 单独检验 MTP |

本轮不混合精简提示词与 MTP。精简组仍要求保留不同根因、严重性、源码位置、利用前提、最小本地验证建议及修复建议，不设置发现数量上限。

## 固定条件

- EC2 `p6-b200.48xlarge`，8 × B200，单机 TP=8。
- 模型 `zai-org/GLM-5.3`，revision `ba32f8c19c8738e2c57c71798c601d477a7bf844`。
- SGLang 0.5.23，同一镜像和同步加载补丁；FP8 KV cache，最大运行请求数 2。
- MTP 参数：`--speculative-algorithm EAGLE --speculative-num-steps 3 --speculative-eagle-topk 1 --speculative-num-draft-tokens 4`。已确认 NextN 模型加载和 speculative decoding 运行；TP0 日志接受长度约 2.40–2.65，接受率约 0.47–0.55。
- 同一源码快照：`agentcore-superagent-update` commit `0a20b8b14ab9abdf7301ec1e475be2d6dc2effde`。
- 四场景：认证授权、文件路径与工作区、Webhook/OAuth、工具执行。
- 每场景分别测试并发 1、2，每种并发重复 5 次。每组 40 条测量请求，另有 4 条预热请求。
- 三组均 `temperature=0`、`reasoning_effort=low`、`max_tokens=32768`。
- 客户端运行在 GPU 实例上，通过 localhost 测量，不经过 SSM 转发。
- 每组开始前清空前缀缓存，再预热全部四场景；因此代表有预热的重复审计负载。

## 指标定义

- **TTFT**：发送请求至第一个生成的流式 delta，包含 reasoning。
- **首次正文**：发送请求至第一个 content delta。
- **TTOT**：发送请求至最后一个生成的 delta。
- **E2E**：发送请求至读取完成事件，包含最后的 usage 和协议开销。
- **近似 TPOT**：`(TTOT − TTFT) / (completion_tokens − 1)`；受 SSE token 合并影响，不等于服务端逐 token 计时。
- 输出 token 包含服务返回 usage 所计入的生成 token；另保存正文字符数和 reasoning 字符数。
- 吞吐量使用该并发批次的总生成 token / 批次墙钟时间。

按并发、场景分别报告均值、p50、p95及相对基线变化。所有原始答案保留，完成、截断、协议错误分别计数。`stop` 且存在正文只说明请求完成，不证明安全结论正确。

## 质量核验与解释边界

抽查每个场景、每种并发的第 1 次响应，比较三组的不同根因、源码证据、利用前提、验证建议和修复建议。将不同措辞的同一根因合并后再比较；新增发现不能直接算正确，缺失基线发现也不能直接算退化，需要回看源码。

本实验是真实仓库源码审计请求的推理性能对照，不是完整 Strix 工具循环，也不执行响应中建议的利用验证。报告分别标明抽查与未核验范围。

三组按 baseline、concise、mtp 顺序运行，并非随机交错。每个场景/并发只有 5 次测量，p95 是描述性估计，不代表生产 SLA。即使温度为零，并发调度和推理内核仍可能导致输出变化；MTP 的端到端时间要结合输出长度与 TPOT 解释。

历史经过 SSM 隧道的测量和 InferenceX 的不同模型、量化、缓存与输出长度数据不作为本轮因果对照。模型加载时间另记录，不计入预热后的单请求 TTOT。

## 执行结果

三组于 2026-11-20 16:20:17 UTC 完成，共 120 次测量及 12 次预热。统计排除预热；全部正式请求正常 stop、有正文且无协议错误。结果见 [测试报告](RESULTS.md)。归档上传验证后停止 GPU，状态见 [资源记录](resource-status.json)。
