# Codex response stream incident — 2026-11-20

Status: unresolved. A successful short request is not evidence that the recurring
disconnect has been fixed.

## Observations

- Error: `stream disconnected before completion: stream closed before response.completed`.
- The active Codex client and app-server binaries inspected during this investigation
  are version 0.171.0.
- The affected conversation uses `us.openai.gpt-6-astra` through
  `amazon-bedrock-runtime` in `us-east-1`. This connection is separate from
  Strix's self-hosted GLM inference connection.
- A log observation at 14:19:01 UTC recorded retry 1/5 after premature stream
  closure. It does not establish that five retries failed.
- The request ID observed around that closure was
  `868b0e77-bebe-4ba7-b057-8ce4d98985f9`.
  A subsequent request ID was `e91e7fe1-c734-4a8f-921c-199a3171d389`.
  These identifiers should accompany any provider-side investigation.
- The observed interval was about 22 seconds. Increasing the default 300-second
  stream idle timeout would not explain or repair an early EOF.
- No HTTP_PROXY, HTTPS_PROXY, ALL_PROXY, or NO_PROXY environment variables were
  present in the inspected process environment. This does not rule out an
  intermediary outside the process.

A further recurrence was logged at **14:44:35 UTC**, again retry 1/5.
The request observed from 14:44:11 through the error was
`74fbe78b-3733-4ea8-aa96-b9f33094bd88` (about 24 seconds).
The subsequent request was `3e7cb542-0a0c-4f68-8e77-3c65befb1242`.
This confirms that the fault persisted during this investigation.

## Configuration restrictions

The inspected provider source's `validate_bedrock_override` permits only
`base_url`, `auth`, `http_headers`, and supported AWS credential/region fields
for the built-in Bedrock provider. Adding `stream_max_retries` or
`stream_idle_timeout_ms` there is rejected; neither is an applied fix.

No completion event was synthesized, no provider endpoint was replaced, and
no daemon was restarted during this investigation.

## Preserved scan results

The four runs were collected under `20261120T131523Z/strix-runs/`, with their
summary in `20261120T131523Z/strix-summary.json`.

| Scenario | Duration |
| --- | ---: |
| Authentication | 372 seconds |
| Paths | 752 seconds |
| Webhooks | 417 seconds |
| Tools | 414 seconds |

The authentication run produced 13 candidate findings. Its WebSocket finding was
subsequently reproduced using the original gateway in an isolated local harness
(see `validation/websocket-local-proof.json`): no credentials, a known synthetic
execution ID, and receipt of a synthetic event. This does not establish exposure
through a deployed application's ingress. Other authentication findings remain
unverified. Completed scanning is not evidence of a healthy Codex response stream.

## Remaining diagnosis

The available evidence establishes premature stream closure, not which hop
caused it. Correlate the request IDs with provider-side response/transport logs
to distinguish upstream generation failure from intermediary connection closure.
Verify any resulting fix with sustained tool-using conversation turns and
explicit terminal response events, rather than short smoke requests alone.
