# GLM-5.3 / 8×B200 多场景测试（非官方）

2026-11-20，孟买 ap-south-1，p6-b200.48xlarge Spot，SGLang TP8。实际自建 GLM-5.3，非 Bedrock 调用。模型版本、镜像和资源信息见 deployment.json、gpu-runtime.json。工具调用往返验证通过（inference-verification.json）。

## 流式推理实测

三个合成代码审计场景（SQL 注入、对象越权、路径遍历），每个并发档各重复 5 次，共 30 次，另有一次不计入的预热。短提示词 142–183 token，输出上限 8192（含 reasoning），高推理强度，温度 0。测试请求在 GPU 主机 loopback 上发送。

| 并发 | TTFT p50 / p95 | E2E p50 / p95 | 平均 TPOT | 总输出吞吐 | 完整可见回答 |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.050 / 0.058 s | 4.225 / 62.437 s | 7.42 ms | 131.7 token/s | 11/15 |
| 2 | 0.051 / 0.510 s | 4.593 / 65.673 s | 7.90 ms | 216.5 token/s | 10/15 |

TTFT 包含 reasoning 首 token；E2E 从请求发出计至完整响应流结束。成功产生可见答案的请求，其首个答案内容 p50 在并发 1/2 下分别为 0.536/0.669 秒；这个统计排除了没有可见答案的请求。TPOT 是 SSE/usage 推算均值，不是逐 token ITL 分布。

HTTP/SSE 错误 0，但 9/30 请求耗尽 8192 token，仅有 reasoning，没有最终答案，均来自路径遍历场景。SQL 注入及对象越权各 10/10 有完整答案；路径遍历仅 1/10。截断请求没有从延迟或吞吐统计中剔除。总 token 吞吐包含无最终答案的推理输出，不能当成有效任务吞吐。暖缓存、重复短提示词以及每档仅 15 个样本限制了结论的适用范围。

## InferenceX 对照

参考页面：https://inferencex.semianalysis.com/infx/inference/glm-5-3 。原始快照见 inferencex-data.json，细节见 methodology.md。

该页面对应组合 GLM-5.2/5.3 分类，抓取的参考记录原始模型字段为 glm5.2，不能把它宣称为已核实的 GLM-5.3。例记录 446074：8×B200、TP8、FP8、SGLang、并发 1，TTFT p50 0.335s，E2E p50 3.645s，平均 TPOT 3.51ms，总吞吐 142.73 token/s。其采用 native MTP、DRAM HiCache，平均输入约 264k token、缓存命中约 97.98%；本次未启用 MTP 或 DRAM offload。模型元数据、引擎和工作负载不同，不计算“快几倍”。

初次启动到服务就绪约 30 分钟，包括下载、权重加载、autotune 和 JIT；不是缓存后重启时间。引擎提示 FP8 KV-cache 默认 scale=1.0，存在数值质量不确定性，没有对照实验证明这是截断原因。

## Strix 实际工具测试

三个场景各运行一次，使用本地合成代码与动态 PoC；没有扫描外部生产服务。Strix 输出上限为 32768，与上面流式测试的 8192 不同。Strix 的非流式请求不提供 TTFT，不能用总扫描耗时代替模型延迟。

| 场景 | 扫描耗时 | LLM 请求数 | 请求 latency p50 / p95 | 结果与修复对照 |
| --- | --- | --- | --- | --- |
| SQL 注入 | 52 s | 10 | 2.544 / 11.355 s | 1 个结构化高危漏洞；OR/UNION 本地 PoC 成功，参数化版本拒绝同样输入 |
| 对象越权 IDOR | 32 s | 7 | 2.737 / 7.472 s | 正文确认高危：alice 读取 bob 文档；修复版本返回 PermissionError；但结构化漏洞数为 0 |
| 路径遍历 | 43 s | 10 | 3.141 / 8.978 s | 1 个结构化中危漏洞；相对路径及绝对路径读越界成功，修复版本均拒绝 |

27 次模型请求均成功返回。三个预置漏洞均在扫描正文中被识别，并报告了修复版本的负对照；但只有两个被正确写入结构化漏洞结果。IDOR 的退出码为 0，因此不能仅凭退出码宣称无漏洞。原始报告、SARIF、coverage、run.json 保存在 `strix-runs/`，汇总见 `strix-summary.json`。保留原始输出，没有人为补写模型遗漏的漏洞记录。

这说明本配置能够执行这三个小型代码审计与工具调用任务，但存在输出预算耗尽、结构化报告遗漏两类可靠性问题。每场景仅一次完整 Strix 运行，不能据此估计大型真实代码库的检出率或稳定性；漏洞等级为 Strix 在合成场景下的判断。

## 资源保留状态

已对 `i-0b33a1d2ee1a2065f` 执行 StopInstances，未执行 terminate。最后核验时间 2026-11-20T07:34:28.038545+00:00，EC2 状态仍为 `stopping`，尚未确认 `stopped`。持久 Spot 请求保留，两块 EBS（200 GiB 根盘、2048 GiB 模型缓存盘）保留且 DeleteOnTermination=false。EBS 保留期间继续计费。资源快照见 final-state.json。
