# H200 实际 Strix 扫描性能

机型：p5en.48xlarge，8 × H200，GLM-5.3 TP8，MTP 3/1/4。


扫描状态：完整完成；扫描 E2E：3419 秒。
成功流式请求：990；失败请求：0。

| 指标 | 均值 | P50 | P95 |
| --- | ---: | ---: | ---: |
| TTFT（秒） | 20.139 | 16.416 | 44.885 |
| 模型请求 E2E（秒） | 24.233 | 20.961 | 58.067 |

8 卡已采集流式输出吞吐：流式流量时间窗口 **99.895 tokens/s**；
已采集流式输出 token / 整次扫描耗时 **99.694 tokens/s**。
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
    "start_epoch": 1795348794,
    "end_epoch": 1795352213,
    "elapsed_s": 3419,
    "exit_code": 2,
    "mode": "deep",
    "ttft_source": "see external performance-summary.json when available"
  },
  "attempts": 1032,
  "successful_streams": 990,
  "failed_attempts": 0,
  "target_commit": "0a20b8b14ab9abdf7301ec1e475be2d6dc2effde",
  "complete_scan": true,
  "non_streaming_requests_excluded_from_model_metrics": 42,
  "usage_coverage": 990,
  "token_metric_scope": "successful_streaming_requests_only; non-streaming output tokens are not captured",
  "ttft_ms": {
    "n": 990,
    "mean": 20138.690652694,
    "p50": 16416.37533300309,
    "p95": 44884.999049148246
  },
  "visible_ttft_ms": {
    "n": 132,
    "mean": 27032.535942098657,
    "p50": 16657.166210497962,
    "p95": 73598.53406480173
  },
  "request_e2e_ms": {
    "n": 990,
    "mean": 24233.03417585754,
    "p50": 20960.780424498807,
    "p95": 58066.6274519448
  },
  "output_tokens": 340855,
  "model_traffic_window_s": 3412.146471261978,
  "output_tokens_per_traffic_window_second": 99.89459798129216,
  "output_tokens_per_scan_second": 99.69435507458321,
  "request_output_tokens_per_second": {
    "n": 990,
    "mean": 25.76426128628277,
    "p50": 10.06628697208687,
    "p95": 112.26112493448349
  },
  "strix": {
    "run_id": "agentcore-superagent-h200_97fd",
    "status": "completed",
    "llm_usage": {
      "requests": 1031,
      "input_tokens": 102415174,
      "output_tokens": 346845,
      "total_tokens": 102762019,
      "cost": 0.0
    },
    "tool_calls": 990,
    "unverified_findings": 72,
    "severity_counts": {
      "critical": 6,
      "medium": 39,
      "high": 17,
      "low": 10
    }
  }
}
```
