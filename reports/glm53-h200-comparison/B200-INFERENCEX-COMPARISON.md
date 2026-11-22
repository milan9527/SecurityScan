# GLM-5.3 B200 与 SemiAnalysis InferenceX 性能对比

整理日期：2026-11-22。本文对比独立流式推理性能，不将完整 Strix 扫描耗时与单次模型请求延迟混用。

## 结论

我们的 B200 部署在低并发下，估算 TPOT 接近 InferenceX 的 FP8 B200 记录：3.653 毫秒对 3.510 毫秒，相差约 4%。我们的 TTFT 数值更低，但输入、缓存、客户端路径和负载不同，不能据此认定整体性能优于 InferenceX。

我们的单请求 E2E 延迟比其 FP8 记录长约 37%，同时平均输出长度多约 38%。两者变化幅度接近，说明解读 E2E 时必须考虑输出长度；这不是对延迟差异的因果验证。

目前结果反映的是各自部署和工作负载下的表现，不能作为同条件硬件排名或 B200 峰值容量结论。

## 单并发数据

我们的机型是 **EC2 p6-b200.48xlarge，8 × NVIDIA B200**，使用 GLM-5.3、TP=8、MTP、FP8 KV cache。FP8 KV cache 不等同于模型权重采用 FP8；不能仅据此与 InferenceX 的精度标签视为相同配置。

| 指标 | 我们的 B200 | InferenceX B200 FP8 + MTP | InferenceX B200 FP4 + MTP |
|---|---:|---:|---:|
| 测试日期 | 2026-11-21 | 2026-10-22 | 2026-11-06 |
| 并发数 | 1 | 1 | 1 |
| TTFT 均值（秒，越低越好） | 0.325 | 0.61160 | 0.55421 |
| E2E latency 均值（秒，越低越好） | 10.220 | 7.44929 | 6.85871 |
| TPOT 均值（毫秒，越低越好） | 3.653（估算） | 3.510 | 3.230 |
| 聚合输出吞吐量（tokens/s） | 263.3 | 142.72678 | 148.31778 |
| 平均输出 tokens / 请求 | 2690.9 | 1952.82890 | 1974.38007 |

选取 FP8 和 FP4 各一条单并发记录展示配置差异，不代表 InferenceX 的所有配方或最佳成绩。表中 InferenceX 记录 ID 分别为 `446074` 和 `447669`。

相对 FP8 记录，我们的 TTFT 数值低约 47%，估算 TPOT 高约 4%；相对 FP4 记录，估算 TPOT 高约 13%。这些比例是不同负载结果的算术比较，不是同条件性能提升或退化。

## 我们的双并发结果

| 指标 | 并发 1 | 并发 2 |
|---|---:|---:|
| 正常完成请求 | 12/12 | 12/12 |
| TTFT 均值（秒） | 0.325 | 0.337 |
| 首次可见正文均值（秒） | 4.353 | 4.973 |
| E2E latency 均值（秒） | 10.220 | 11.111 |
| 估算 TPOT 均值（毫秒） | 3.653 | 4.209 |
| 聚合输出吞吐量（tokens/s） | 263.3 | 447.5 |

双并发吞吐量比单并发提高约 70%。本轮仅覆盖并发 1、2，不能据此确定饱和吞吐量。

## 指标定义

- **TTFT**：我们的统计从请求发出到首个生成内容分块到达，包括 reasoning 或 tool calls；不等于首次最终回答正文出现。单并发首次可见正文均值为 4.353 秒。
- **E2E latency**：从请求发出到完整响应流结束的端到端延迟。本文统一使用 E2E，不使用含义容易混淆的 TTOT。
- **估算 TPOT**：我们的计算为 `(最后生成增量到达耗时 − TTFT) / (输出 tokens − 1)`，再换算为毫秒。客户端分块可能包含多个 token，因此不属于逐 token 到达时间的直接测量。
- **聚合输出吞吐量**：我们的统计为输出 token 总数除以批次墙钟时间，包括模型返回的 reasoning token 计数，是整个 8 卡服务的吞吐量，不是每卡吞吐量。
- **InferenceX 字段**：使用 `mean_ttft`、`mean_e2el`、`mean_tpot`、`output_tput_tps` 和 `mean_output_tokens_actual`。前三个原始字段以秒为单位；TPOT 在表中乘以 1000。没有用包含输入 token 的总吞吐字段替代输出吞吐量，也没有将页面的中位数或分位数与我们的均值混比。

## 可比性限制

### 工作负载与缓存不同

我们的测试使用 auth、path、webhook、tools 四组离线代码审计提示词，每组预热一次；每种并发各运行 12 个正式请求。温度为 0，reasoning effort 为 low，输出上限为 8192 tokens。

InferenceX 所选记录属于 `agentic_traces`。FP8 记录平均输入约 264408 tokens、报告的 GPU cache hit rate 约 97.98%；FP4 记录平均输入约 272578 tokens、该命中率约 98.07%。大量缓存复用使平均输入长度不能直接当作每次实际需要重新计算的 prefill 长度。

请求序列、间隔、输入输出长度、缓存和调度方式不同，所以不能把 263.3 对 142.7 tokens/s 解释为我们的服务容量更高。

### 推理环境与测量方式不同

我们的 B200 位于孟买区域，测试客户端通过 SSM 隧道连接；使用 SGLang、TP=8、MTP/EAGLE 3 steps、top-k=1、4 draft tokens。InferenceX 的镜像、精度、缓存与其他服务参数需要逐项对齐。

我们的 TPOT 是客户端估算值。双方还需要核实 TTFT 是否同样计入 reasoning、输出 token 计数是否一致，以及请求完成边界是否一致，才适合做严格对照。每种并发仅 12 个样本，尚不足以评价稳定的尾延迟。

### 页面模型名称与原始标签存在映射歧义

InferenceX 页面路径为 `glm-5-3`，但上述 B200 原始记录的 `model` 字段为 `glm5.2`。核对页面前端代码发现，`glm5.2` 和 `glm5.3` 都被映射到 `GLM-5.2`；页面使用的查询键也为 `GLM-5.2`。

因此，不能单凭原始标签断定 B200 测试使用了不同模型，也不能确认与我们的 GLM-5.3 权重一致。实际 checkpoint 和 revision 仍需从对应运行配方核实。此前仅凭标签区分 GLM-5.2 与 GLM-5.3 的判断不应视为已证实结论。

## 如何进行严格对照

后续应固定模型 checkpoint、权重与 KV cache 精度、SGLang 镜像、MTP 参数、TP 数量、输入输出长度、并发、缓存状态和客户端位置，并采用相同的 agentic traces 或固定长度测试集。分别报告 TTFT、首次正文延迟、E2E、TPOT、输出吞吐量及样本量，再增加并发以测量饱和点。

## 数据来源

- [本项目 B200/H200 独立流式测试报告](README.md)
- [本项目指标汇总](comparison.json)
- [已保存的 InferenceX 原始数据](../glm53-multiscenario/inferencex-data.json)
- [SemiAnalysis GLM-5.3 页面](https://inferencex.semianalysis.com/infx/inference/glm-5-3)
- [页面数据接口](https://inferencex.semianalysis.com/api/v1/benchmarks?model=GLM-5.2)（动态数据，后续可能更新）
- [FP8 B200 对应运行](https://github.com/SemiAnalysisAI/InferenceX/actions/runs/39707633720/attempts/1)
- [FP4 B200 对应运行](https://github.com/SemiAnalysisAI/InferenceX/actions/runs/40484444761/attempts/1)
