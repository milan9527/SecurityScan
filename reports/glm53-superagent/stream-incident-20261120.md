# Codex response stream incident — 2026-11-20

Status: unresolved. A successful short request is not evidence that the recurring
disconnect has been fixed.

## 2026-11-21 retry exhaustion and current blocker

The response stream failed through all five retries, ending at 03:15:48 UTC.
The client recorded two parse errors before each premature closure:

```text
error_category=Data error_line=1 error_column=162 payload_bytes=162
error_category=Syntax error_line=1 error_column=2 payload_bytes=6
```

The event bodies were not retained in the available logs. Their lengths do not
identify their content or establish an upstream error code.

Request IDs for provider-side correlation, in chronological order:

| Request time UTC | Request ID |
| --- | --- |
| 03:13:38 | c6e926fa-b06f-4267-9e79-662bf5402c0f |
| 03:13:52 | fac290ec-a349-48ab-9669-24d4a42a557b |
| 03:14:13 | 32192558-0371-4433-aace-7317797edd20 |
| 03:14:26 | b75cc185-c3f1-4726-9e70-cbd994fd1a8c |
| 03:14:48 | bc055756-62a2-4ba0-b724-52d51ac9203a |
| 03:15:31 | 5c673a10-9e5a-4072-acc4-26371224e72a |

The endpoint was Bedrock Runtime's `/openai/v1/responses` in `us-east-1`.
Obtain the corresponding error-event body and termination reason from the
provider, then determine whether the provider emitted an incompatible event
or the client failed to handle a valid error. No provider support message has
been sent.

The request carried `remote_compaction_v2`, but the installed
`codex features list` marks that flag as removed. Disabling it is not an
established fix. No model/provider change or speculative flag override was
applied.

At 03:20:37 UTC, SSM command `ea5e2561-cd61-4842-8252-83b8ab5700be`
completed successfully and found no running Docker containers, Strix processes,
or SGLang processes. The full scan had not started. A subsequent EC2
`StopInstances` call succeeded and returned `stopping`; no terminate call was made.

Diagnostic reference:
https://learn.chatgpt.com/docs/config-file/environment-variables#diagnostics
describes targeted `RUST_LOG` filters and opt-in plaintext logs. This does not
recover the missing bodies of earlier failed events or establish a repair.

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

## Recurrence on 2026-11-21

At 02:59:44 UTC and 03:00:03 UTC the client logged retries 1/5 and 2/5,
respectively, for the same premature stream closure:

| Closure (UTC) | Request ID |
| --- | --- |
| 02:59:44 | `aa230621-2ed1-4e85-9527-c39deaa72434` |
| 03:00:03 | `866e833d-2edd-4b43-bd35-2c8ceda284a0` |

Immediately before each closure, `codex_api::sse::responses` logged two
`Failed to parse SSE event` messages:

- Data error at line 1, column 162; payload size 162 bytes.
- Syntax error at line 1, column 2; payload size 6 bytes.

The inspected SQLite logs contain no raw event bodies for this interval.
Payload lengths alone cannot identify an upstream error or a completion marker.
The public `openai/codex` main-branch `codex-rs/codex-api/src/sse/responses.rs`
source skips events that fail JSON deserialization and reports
`stream closed before response.completed` when the stream ends without a
terminal response. This source inspection is consistent with the logs, but
is not a verification of the exact installed binary's source or the root cause.

A subsequent request, `aa437639-7bd4-4cb8-98ec-191de0f42d16`, delivered a tool
call at 03:00:05 UTC. Retry recovery is not a permanent fix. The GitHub latest
release endpoint returned `rust-v0.171.0`, matching the installed version at
the time of inspection; no newer release was identified as a repair.

The full Strix scan had not started. A remote process check found no Strix or
benchmark process, and an EC2 stop request was issued for the idle GPU
instance `i-0b33a1d2ee1a2065f` in `ap-south-1`. The instance was not terminated.

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
In particular, obtain the failed event bodies through a controlled, redacted
diagnostic capture or provider-side trace. Broad SSE trace logging can include
conversation content and tool arguments, so it was not enabled automatically.
Verify any resulting fix with sustained tool-using conversation turns and
explicit terminal response events, rather than short smoke requests alone.
