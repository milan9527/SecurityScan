# H200 实际 Strix 扫描性能

机型：p5en.48xlarge，8 × H200，GLM-5.3 TP8，MTP 3/1/4。


扫描状态：完整完成；扫描 E2E：841 秒。
成功流式请求：332；失败请求：0。

| 指标 | 均值 | P50 | P95 |
| --- | ---: | ---: | ---: |
| TTFT（秒） | 1.136 | 0.984 | 2.041 |
| 模型请求 E2E（秒） | 2.752 | 1.769 | 7.734 |

8 卡已采集流式输出吞吐：流式流量时间窗口 **120.153 tokens/s**；
已采集流式输出 token / 整次扫描耗时 **118.985 tokens/s**。
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
    "start_epoch": 1795427538,
    "end_epoch": 1795428379,
    "elapsed_s": 841,
    "exit_code": 2,
    "mode": "deep",
    "ttft_source": "see external performance-summary.json when available"
  },
  "attempts": 333,
  "successful_streams": 332,
  "failed_attempts": 0,
  "target_commit": "d7b9a6176ab4e279465ba3ee09922cde2b74de47",
  "complete_scan": true,
  "non_streaming_requests_excluded_from_model_metrics": 1,
  "usage_coverage": 332,
  "token_metric_scope": "successful_streaming_requests_only; non-streaming output tokens are not captured",
  "ttft_ms": {
    "n": 332,
    "mean": 1136.0342093795193,
    "p50": 984.3532274971949,
    "p95": 2041.266920602356
  },
  "visible_ttft_ms": {
    "n": 74,
    "mean": 3809.695026621567,
    "p50": 2627.1349210001063,
    "p95": 9334.97290805389
  },
  "request_e2e_ms": {
    "n": 332,
    "mean": 2751.826211373598,
    "p50": 1769.2781444930006,
    "p95": 7734.346808948611
  },
  "output_tokens": 100066,
  "model_traffic_window_s": 832.8210906982422,
  "output_tokens_per_traffic_window_second": 120.153057022252,
  "output_tokens_per_scan_second": 118.9845422116528,
  "request_output_tokens_per_second": {
    "n": 332,
    "mean": 80.01280512123925,
    "p50": 67.7610731616978,
    "p95": 168.5547058975306
  },
  "strix": {
    "run_id": "gitlab_aee7",
    "status": "completed",
    "llm_usage": {
      "requests": 332,
      "input_tokens": 31835464,
      "output_tokens": 100066,
      "total_tokens": 31935530,
      "cost": 0.0
    },
    "tool_calls": 332,
    "unverified_findings": 1,
    "severity_counts": {
      "medium": 1
    }
  }
}
```
