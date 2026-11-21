# GLM-5.3 additional full Strix scans

Self-hosted GLM-5.3 / SGLang / TP8 / MTP / p6-b200.48xlarge.

Deep mode; full scope; sequential scans to avoid cross-scan contention.

Non-streaming request latency is not TTFT or streaming TTOT. Findings require independent verification. EC2 was running at the time of this test; this is not a live resource status.

## agentcoreshell-deep

```json
{
  "case": "agentcoreshell-deep",
  "target": "/home/ec2-user/bedrock/AgentcoreShell",
  "status": "completed",
  "elapsed_s": 120,
  "runner_pid": 2042326,
  "run_id": "agentcoreshell_529c",
  "requests": 66,
  "outcomes": {
    "success": 66
  },
  "tool_calls": 66,
  "unverified_findings": 1,
  "severity": {
    "high": 1
  },
  "request_mean_ms": 1829.2575757575758,
  "request_p95_ms": 4511,
  "exit_code": 2,
  "runner_finished": true
}
```

## superagent-frontend-deployment

```json
{
  "case": "superagent-frontend-deployment",
  "target": "/home/ec2-user/bedrock/agentcore-superagent-update",
  "status": "completed",
  "elapsed_s": 781,
  "runner_pid": 2053539,
  "run_id": "agentcore-superagent-update_9497",
  "requests": 575,
  "outcomes": {
    "success": 575
  },
  "tool_calls": 559,
  "unverified_findings": 28,
  "severity": {
    "medium": 9,
    "low": 3,
    "high": 6,
    "critical": 3,
    "info": 7
  },
  "request_mean_ms": 2846.817391304348,
  "request_p95_ms": 8985,
  "exit_code": 2,
  "runner_finished": true
}
```

