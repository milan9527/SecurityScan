# H200 实际 Strix 扫描性能

机型：p5en.48xlarge，8 × H200，GLM-5.3 TP8，MTP 3/1/4。


扫描状态：完整完成；扫描 E2E：519 秒。
成功流式请求：437；失败请求：0。

| 指标 | 均值 | P50 | P95 |
| --- | ---: | ---: | ---: |
| TTFT（秒） | 1.291 | 1.104 | 2.278 |
| 模型请求 E2E（秒） | 2.251 | 1.749 | 5.461 |

8 卡已采集流式输出吞吐：流式流量时间窗口 **142.974 tokens/s**；
已采集流式输出 token / 整次扫描耗时 **141.040 tokens/s**。
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
    "start_epoch": 1795422710,
    "end_epoch": 1795423229,
    "elapsed_s": 519,
    "exit_code": 0,
    "mode": "deep",
    "ttft_source": "see external performance-summary.json when available"
  },
  "attempts": 438,
  "successful_streams": 437,
  "failed_attempts": 0,
  "target_commit": "fecbb16aa07c5aa7d03a454dda9577545a1df9ab",
  "complete_scan": true,
  "non_streaming_requests_excluded_from_model_metrics": 1,
  "usage_coverage": 437,
  "token_metric_scope": "successful_streaming_requests_only; non-streaming output tokens are not captured",
  "ttft_ms": {
    "n": 437,
    "mean": 1291.0114650368344,
    "p50": 1104.1334530018503,
    "p95": 2278.2188580022184
  },
  "visible_ttft_ms": {
    "n": 23,
    "mean": 2813.625196825698,
    "p50": 2117.1675689984113,
    "p95": 6706.081379708483
  },
  "request_e2e_ms": {
    "n": 437,
    "mean": 2250.555517119285,
    "p50": 1748.5785520111676,
    "p95": 5461.174779795692
  },
  "output_tokens": 73200,
  "model_traffic_window_s": 511.98160910606384,
  "output_tokens_per_traffic_window_second": 142.97388558118234,
  "output_tokens_per_scan_second": 141.04046242774567,
  "request_output_tokens_per_second": {
    "n": 437,
    "mean": 60.42736458817966,
    "p50": 54.24774324596825,
    "p95": 126.32310589512123
  },
  "strix": {
    "run_id": "airflow_74a0",
    "status": "completed",
    "llm_usage": {
      "requests": 437,
      "input_tokens": 42331036,
      "output_tokens": 73200,
      "total_tokens": 42404236,
      "cost": 0.0
    },
    "tool_calls": 437
  }
}
```
