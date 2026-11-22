# Security Penetration Test Report

**Generated:** 2026-11-20 13:41:04 UTC

# Executive Summary

An authorized white-box security assessment of the **AgentCore Demo Platform** (`super-agent/backend`, Fastify + Prisma) focused on webhook and outbound-request security identified three high-severity vulnerabilities, all dynamically validated against local loopback mocks only.

**Overall risk posture:** Elevated — both the inbound webhook boundary and the outbound request boundary lack any effective enforcement.

**Key findings**
- **Full-response SSRF** in workflow `api_call` action nodes: attacker-supplied URLs are fetched with no scheme/host/IP validation, redirects are followed, and the complete response body is returned to the caller. Reachable by authenticated low-privilege users and indirectly through the unauthenticated webhook trigger.
- **Unauthenticated workflow execution** via the public webhook trigger endpoint: the per-webhook secret generated at creation is never verified on the trigger path, so knowing the webhook URL is the only credential and requests are trivially replayable.
- **Unauthenticated IM webhook message injection**: the generic IM webhook endpoint performs no authentication, signature, or replay checks, allowing arbitrary agent message injection and agent execution.

**Business impact**
- Internal network probing with full response disclosure from the application server (SSRF).
- Unauthorized, repeatable triggering of workflows and agent conversations — compute cost, unintended automated actions, and potential data exfiltration through chained agent capabilities.

# Methodology

**Engagement type:** White-box source-code assessment of the local repository; validation restricted to local loopback mock HTTP servers per engagement rules (no deployed endpoints, no real credentials, no cloud metadata contacted).

**Framework:** OWASP WSTG-aligned, focused on the webhook/outbound-request scenario: callback verification, replay protection, URL validation, redirect handling, and SSRF boundaries.

**Activities:** repository mapping of webhook routes/services, IM adapters, outbound HTTP call sites; source-to-sink tracing of attacker-controlled input through actual guards; local PoC construction (Fastify route registration with mocked dependencies; loopback HTTP servers for SSRF/redirect validation); coverage recording for every assessed surface including clean ones (OAuth flow, litellm routes, skill marketplace, insforge orchestrator, public status endpoint).

**Scope boundaries honestly reported as not fully covered within budget:** the IM adapter signature schemes were assessed via the generic webhook path only; the `a2a-client.service.ts` remote-invocation sink has no URL validation but no current attacker-controlled entry point (recorded as an open watch item, not reported); `eval()` usage in action-executor transform actions was noted but outside this scenario's scope.

# Technical Analysis

**Severity model:** exploitability × demonstrated impact; all three findings were validated with local executable PoCs.

1. **Full-response SSRF via `api_call` action node** (High, CVSS 7.7) — `ActionNodeExecutor.executeApiCall` (`action-executor.ts:137` fetch) and `WorkflowOrchestrator.executeActionNode` (`workflow-orchestrator.ts:554`) fetch `apiConfig.url` with zero validation: no scheme allowlist, no host/IP restriction, no redirect re-validation. The full response body is returned to the caller. Reachable via `POST /api/workflows` + `/:id/execute-v2` (authenticated low-privilege) and via the unauthenticated webhook trigger path. Locally demonstrated: 302 redirect to a loopback server returned the internal body. A related blind SSRF exists in the MCP test-connection endpoint (`mcp.service.ts:245`, HEAD with attacker headers to user-registered hosts).

2. **Unauthenticated workflow execution via webhook trigger** (High, CVSS 7.0) — `POST /api/v1/webhook/:webhookId/trigger` (`webhooks.routes.ts:315`, no `authenticate` preHandler) reaches `triggerWebhook` (`webhook.service.ts:137-186`), which checks only existence, `isEnabled`, and an optional IP allowlist. The generated `secretHash` (`webhook.service.ts:50-53`) is never compared anywhere in the codebase. PoC: request with no secret header returns `200 {received:true}`; wrong `x-webhook-secret` ignored; unlimited identical replays each create executions.

3. **Unauthenticated IM webhook message injection** (High, CVSS 7.0) — `POST /api/im/webhook/:bindingId` performs no authentication, signature verification, or replay protection; any network caller who knows a binding UUID injects arbitrary text into the agent chat pipeline, triggering agent execution and chat creation.

**Systemic themes:** secrets are generated but never enforced; public "trigger-style" endpoints treat URL knowledge as sufficient authentication with no replay defense; all outbound fetches lack a centralized SSRF guard (scheme/host/IP/redirect policy).

**Clean surfaces (coverage recorded, no issue found / not attacker-controlled):** OAuth token exchange (fixed provider URLs), litellm routes (server-config base URL only), skill marketplace (host-pinned URL construction), insforge orchestrator (config-derived host), public webhook status endpoint (unguessable UUID, low-value data only).

# Recommendations

**Immediate**
1. Enforce webhook secrets: on `POST /v1/webhook/:webhookId/trigger`, require an `X-Webhook-Secret` (or HMAC signature) header and verify it timing-safely against the stored `secretHash` before creating the call record; add timestamp/nonce replay protection.
2. Add authentication (shared secret or platform signature) to `POST /api/im/webhook/:bindingId`.

**Short-term**
3. Introduce a centralized SSRF guard for all outbound requests from workflow execution: scheme allowlist (http/https), deny private/link-local/loopback/metadata IP ranges (resolving hostnames before the request), manual redirect handling with per-hop re-validation, and response size limits. Apply it to `action-executor.ts`, `workflow-orchestrator.ts`, and `mcp.service.ts`.
4. Add per-node schema validation for workflow nodes (including `metadata.apiConfig`) so unvalidated URL fields cannot reach the fetch sink.
5. Restrict workflow `api_call` destinations to operator-configured allowlists or per-organization egress policies.

**Medium-term**
6. Add rate limiting and audit logging on public trigger endpoints; review the `eval()` usage in action-executor transform actions (noted but out of scope for this assessment).
7. Flip the PoC test left at `tests/unit/webhook-trigger-authz.poc.test.ts` into a regression test asserting the fixed behavior.

**Retest & validation:** after remediation, re-run the SSRF loopback redirect PoC (must be blocked with re-validation on every hop) and the webhook trigger PoC (must reject requests lacking a valid secret and reject replays).

