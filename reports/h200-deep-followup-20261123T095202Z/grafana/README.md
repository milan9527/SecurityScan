# H200 实际 Strix 扫描性能

机型：p5en.48xlarge，8 × H200，GLM-5.3 TP8，MTP 3/1/4。


扫描状态：完整完成；扫描 E2E：2254 秒。
成功流式请求：482；失败请求：0。

| 指标 | 均值 | P50 | P95 |
| --- | ---: | ---: | ---: |
| TTFT（秒） | 1.129 | 0.981 | 2.222 |
| 模型请求 E2E（秒） | 2.178 | 1.311 | 6.317 |

8 卡已采集流式输出吞吐：流式流量时间窗口 **41.710 tokens/s**；
已采集流式输出 token / 整次扫描耗时 **41.527 tokens/s**。
两者均包含相应时间窗口内的工具与编排间隔，不是 GPU 连续解码速度。

TTFT：控制端代理向上游发出请求至首个非空 reasoning/content/tool 增量抵达；首段可见正文另列。
模型请求 E2E：请求发出至响应读完，包含排队、推理和 SSM 网络开销。
扫描 E2E：包含 Strix 编排、模型与工具调用，不含模型权重加载。
吞吐量为 8 卡整体，不是单卡；输出 token 使用服务端 usage（含 reasoning）。
请求吞吐量、首个至最后一个成功流式请求的时间窗口吞吐量、流式 token / 整次扫描耗时分别列出。
如果 usage_coverage 少于 successful_streams，token 吞吐量不完整，不能直接比较。
Strix 自带首事件计时不作为此处 TTFT。自动发现仍需独立核验。
所有非流式请求（包括连通性预检）均不计入模型性能分布，但包含在扫描整体耗时与 attempts 中。
当前代理未采集非流式输出 token，因此上述 token 总数与吞吐量只覆盖成功流式请求，不代表全部扫描输出。
若 complete_scan 为 false，以下指标仅描述中断前的部分流量，不代表完整扫描成绩。

```json
{
  "hardware": "p5en.48xlarge / 8 x NVIDIA H200 / TP8",
  "model": "GLM-5.3 / SGLang / MTP 3/1/4",
  "serving_config": {
    "region": "ap-northeast-1",
    "sglang_version": "0.5.23",
    "tensor_parallel_size": 8,
    "context_length": 262144,
    "max_running_requests": 2,
    "mem_fraction_static": 0.8,
    "chunked_prefill_size": 8192,
    "kv_cache_dtype": "fp8_e4m3",
    "max_output_tokens": 32768,
    "reasoning_effort": "low"
  },
  "scan_status": {
    "start_epoch": 1795428399,
    "end_epoch": 1795430653,
    "elapsed_s": 2254,
    "exit_code": 2,
    "mode": "deep",
    "ttft_source": "see external performance-summary.json when available"
  },
  "attempts": 483,
  "successful_streams": 482,
  "failed_attempts": 0,
  "target_commit": "fffbace06b623ea8a5186b28f27305277a41de8f",
  "complete_scan": true,
  "non_streaming_requests_excluded_from_model_metrics": 1,
  "usage_coverage": 482,
  "token_metric_scope": "successful_streaming_requests_only; non-streaming output tokens are not captured",
  "ttft_ms": {
    "n": 482,
    "mean": 1128.8350221909402,
    "p50": 981.0060855015763,
    "p95": 2221.5567576546164
  },
  "visible_ttft_ms": {
    "n": 45,
    "mean": 4863.567168956635,
    "p50": 2428.871299009188,
    "p95": 18955.961790395657
  },
  "request_e2e_ms": {
    "n": 482,
    "mean": 2177.6840035331193,
    "p50": 1311.3526990055107,
    "p95": 6316.629727747195
  },
  "output_tokens": 93602,
  "model_traffic_window_s": 2244.094257593155,
  "output_tokens_per_traffic_window_second": 41.71036919830203,
  "output_tokens_per_scan_second": 41.52706299911269,
  "request_output_tokens_per_second": {
    "n": 482,
    "mean": 60.55312687419519,
    "p50": 46.29975923801752,
    "p95": 150.35334288023333
  },
  "strix": {
    "run_id": "grafana_d22c",
    "status": "completed",
    "llm_usage": {
      "requests": 482,
      "input_tokens": 42862045,
      "output_tokens": 93602,
      "total_tokens": 42955647,
      "cost": 0.0
    },
    "tool_calls": 482,
    "unverified_findings": 1,
    "severity_counts": {
      "medium": 1
    }
  }
}
```
