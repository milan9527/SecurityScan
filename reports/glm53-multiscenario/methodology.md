# GLM-5.3 multiple security scenarios — Unofficial benchmark

## Scope and ground truth

Three synthetic local Python applications cover SQL injection, document object
access control, and download path traversal. Each includes a vulnerable function
and a corrected control. `verify-fixtures.py` verifies ground truth locally;
these checks are not model findings. Strix independently reviews each directory
with tool execution in its sandbox. No external application is a target.

## Measurements

Inference runs on the GPU host through loopback HTTP, separately from Strix.
All timings use a monotonic clock starting before HTTP dispatch:

- TTFT: first nonempty generated SSE delta, including reasoning tokens.
- First visible: first nonempty answer-content delta; reasoning may precede it.
- E2E latency: time until the SSE response ends with `[DONE]`.
- Approximate TPOT: `(time to last generated delta - TTFT) / (completion_tokens - 1)`.
  SSE chunks may batch tokens; this is not a per-token ITL distribution.
- Aggregate throughput: total completion tokens divided by the stage wall time.
  Completion tokens include reasoning as reported by the server.

One excluded warmup precedes concurrency 1 and concurrency 2 stages. Each stage
repeats each of the three natural code-audit prompts five times. No cache flush
occurs between requests: these are warm repeated application workloads, not cold
prefill benchmarks. Record actual prompt/output tokens and length truncations.
The p95 is a descriptive interpolated sample quantile, not a stable population
estimate with only 15 requests per stage. Errors remain in raw results and are
reported separately. A missing DONE, finish reason or usage is an error.

Strix elapsed time includes model requests, sandbox execution, orchestration and
report writing over the SSM tunnel. It is not inference latency. Streaming is
disabled for Strix; model TTFT comes only from the separate streaming benchmark.
Temperature is zero for inference measurements; a single Strix run per scenario
does not establish statistically reliable vulnerability-detection accuracy.
The streaming generation cap is 8192 tokens, including reasoning; actual lengths
and finish reasons determine whether a response completed within that cap.
Strix uses a separate 32768-token cap per model request and high reasoning effort.
Its task completion must not be interpreted as completion under the streaming
benchmark's smaller token budget.

## InferenceX reference

Requested dashboard: https://inferencex.semianalysis.com/infx/inference/glm-5-3

Data captured 2026-11-20 from
https://inferencex.semianalysis.com/api/v1/benchmarks?model=GLM-5.2
The dashboard maps this route to a combined GLM-5.2/5.3 category. Raw records
identify `glm5.2`; do not relabel them as verified GLM-5.3 measurements.
Raw snapshot: `inferencex-data.json`. Upstream methodology snapshot:
`inferencex-methodology.md` (https://github.com/SemiAnalysisAI/InferenceX).

Example reference record 446074, dated 2026-10-22: 8 B200, SGLang, FP8,
TP8, concurrency 1, native MTP and DRAM HiCache offload enabled; agentic traces,
263 completed requests. Mean input 264407.9 tokens, mean output 1952.8 tokens,
server cache-hit ratio 97.98%. Mean/p50/p95 TTFT: 0.61160/0.33549/2.23077 s;
mean/p50/p95 E2E: 7.44929/3.64507/24.70287 s. Mean TPOT 3.51 ms;
output throughput 142.72678 tokens/s. These are third-party reference values,
not measurements of this deployment.

Our deployment uses GLM-5.3 pinned revision, FP8, TP8, no MTP, no DRAM offload,
262144 context and short application-specific prompts. Different model metadata,
engine revisions, caching and workloads prevent a defensible speedup ratio.

## Startup and numerical caveats

The instance launched at 06:47:07 UTC and inference became ready at approximately
07:17:02 UTC on 2026-11-20. This includes image preparation, first download,
weight loading, autotuning and kernel compilation; it is not a cached restart
measurement. Weight loading took approximately 765 seconds. The retained EBS
model cache contains approximately 704 GiB.

The engine reported FP8 KV-cache scales defaulting to 1.0. This is a possible
numerical-quality limitation of the deployed configuration. There is no
controlled comparison establishing that it caused any reasoning truncation.
Keep truncated requests in latency and throughput statistics and report answer
completion separately. These runs measure the configuration actually deployed,
not an optimized upper bound for B200 or GLM-5.3.
