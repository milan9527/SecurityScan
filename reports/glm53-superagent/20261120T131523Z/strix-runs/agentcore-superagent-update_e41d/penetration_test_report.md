# Security Penetration Test Report

**Generated:** 2026-11-20 13:21:35 UTC

# Executive Summary

An authorized white-box security assessment of the **Super Agent Platform** backend (Fastify/TypeScript/Prisma) focused on authentication and tenant isolation identified **13 findings: 1 critical, 4 high, 5 medium, 2 low, 1 informational**. Overall risk posture is **poor**: the platform's central authentication and multi-tenant boundaries can be bypassed by unauthenticated or low-privileged attackers through several independent paths.

**Key findings**
- **Critical — forged internal service tokens (vuln-0003):** the internal-token HMAC key in Cognito mode is the *public* Cognito userPoolId, which an unauthenticated `GET /api/auth/config` endpoint reveals; a forged token authenticates as any user/role/org with no profile lookup. Proven by local PoC.
- **High — hardcoded default JWT secret (vuln-0001):** when `JWT_SECRET` is unset (local mode), the well-known default allows forging session JWTs for any user/role/org; the token's `role`/`orgId` claims are trusted when no membership row exists. Proven by local PoC.
- **High — cross-org agent admin (vuln-0004):** agent access checks trust `agent_permissions` rows with no organization binding; `:permId` update/delete routes act on raw IDs. Validated locally.
- **High — unauthenticated IM webhook (vuln-0007, medium-rated by scope of impact):** `POST /api/im/webhook/:bindingId` has no signature verification (unlike its WhatsApp sibling), executes the victim org's agent on attacker text, creates sessions, injects messages into bound IM channels, and returns the agent's reply to the attacker. Proven by local PoC.
- **High — unauthenticated WebSocket gateway (vuln-0010):** `/ws/executions` performs no authentication or ownership check; any client can subscribe to any org's execution events including node logs and outputs.
- Additional findings: unscoped membership mutation (vuln-0002), member-level chat-history IDOR (vuln-0006), hardcoded `INSFORGE_JWT_SECRET` default (vuln-0008), session JWTs in URLs (vuln-0005), and four reachable/known dependency CVEs (js-yaml, nodemailer, fastify, ws).

**Business impact:** complete authentication bypass on Cognito-mode deployments, cross-tenant administrative control, exposure of customer chat and workflow execution data, and unauthenticated invocation of customer agents.

# Methodology

Conducted as an authorized white-box source-code assessment with local-only validation, per the engagement rules: no deployed endpoints were contacted, no real credentials used, and no cloud resources changed.

**Scope:** `/workspace/agentcore-superagent-update` (backend primary; frontend and dependency manifests included for supply-chain review).

**Approach**
- Manual source tracing of public, internal, and session routes through middleware (`authenticate`, `requireRole`, `requirePermission`, `requireScopeAccess`, `agentAccess`) to Prisma sinks.
- Secret derivation review (JWT secret, internal HMAC key, widget API-key hashing) with a public-route disclosure cross-check.
- Tenant-isolation audit of all route handlers for org/owner-unbound queries.
- Static supply-chain pass: opengrep (taint mode), gitleaks, trufflehog, trivy fs, bounded ast-grep over `backend/src`.
- Validation with minimal local regression tests: vitest suites using mocked Prisma and Fastify `inject()` reproducing each finding (e.g. `tests/unit/auth-forgery.poc.test.ts`, `tests/unit/tenant-isolation.audit.test.ts`, `tests/unit/im-webhook-auth.poc.test.ts`). Findings without an executed local repro are explicitly marked lower confidence.

**Honest coverage notes:** clean sweeps confirmed for widget-auth, Cognito login-migration, documents/apiKeys/files/users/workflows routes, and base repositories. Not covered: frontend `xlsx` import-level reachability, agentcore/app-hosting PoC manifest CVEs, agent-side tool permissions, and live WebSocket replay (static trace only).

# Technical Analysis

**Severity model:** exploitability × demonstrated impact, calibrated to evidence produced this scan.

**Authentication weaknesses**
1. **Internal token forgery, critical (vuln-0003):** `verifyInternalToken` HMACs with `INTERNAL_TOKEN_SECRET = userPoolId` in Cognito mode (`backend/src/middleware/auth.ts:79-80`). The pool ID is returned by unauthenticated `GET /api/auth/config` (`backend/src/routes/auth.routes.ts:29-40`). A forged `internal.<payload>.<sig>` token is accepted *before* any profile lookup, so arbitrary `sub`/`orgId`/`role` claims become the request identity. Local PoC demonstrated forged acceptance.
2. **Default JWT secret, high (vuln-0001):** `JWT_SECRET` defaults to the hardcoded string at `backend/src/config/index.ts:30` with no startup guard; a forged local-mode JWT authenticates as any user, and `role`/`orgId` claims are trusted when no membership row exists (`auth.ts:230-236`). Local PoC demonstrated.
3. **InsForge token minting, high (vuln-0008):** hardcoded default `INSFORGE_JWT_SECRET` (`config/index.ts:145`) is used to HMAC access tokens minted at `routes/apps.routes.ts:453`.

**Tenant isolation weaknesses**
4. **Cross-org agent admin, high (vuln-0004):** `agentAccess.service.ts` reads `agent_permissions` keyed only by `(agent_id, user_id)` with no `organization_id`; `agentPermissions.routes.ts` `:permId` update/delete handlers act on raw IDs. Validated locally.
5. **Unauthenticated IM webhook, medium (vuln-0007):** no signature verification on `POST /api/im/webhook/:bindingId` (`im.routes.ts:736`); handler fetches the binding by ID and runs the victim's agent on attacker text via `imService.handleMessage` → `chatService.processMessage` as `binding.created_by`; the agent reply is returned to the caller, and 200-vs-404 responses enumerate binding IDs. Executed PoC.
6. **Unauthenticated execution gateway, medium (vuln-0010):** `/ws/executions` (`execution.gateway.ts:125-142`) discards the request and validates only that `executionId` is non-empty; `broadcastEvent` sends full workflow events (node status, logs, outputs) to all subscribers. Complete static trace; no live WS replay.
7. **Cross-scope membership manipulation, medium (vuln-0002):** scope-membership routes authorize on path scope `:id` but mutate `:membershipId` with no scope binding; `requireScopeAccess` also fails open when no scope ID is present.
8. **Member-level chat IDOR, medium (vuln-0006):** chat session/history reads filter by org but not `user_id`, though the list endpoint filters per-user — proving the intent.

**Systemic root causes:** (a) secret derivation from public or default values with no startup enforcement; (b) authorization middleware that fails open when identifiers are absent; (c) secondary-ID mutations unbound to the authorized parent object; (d) unauthenticated event/webhook channels without signature or ownership checks. Individual reports (vuln-0001 through vuln-0013) carry full reproduction steps and code locations.

# Recommendations

**Immediate**
1. Replace the internal-token HMAC key with a dedicated high-entropy `INTERNAL_TOKEN_SECRET`; never derive it from the public `userPoolId` (vuln-0003).
2. Make `JWT_SECRET` and `INSFORGE_JWT_SECRET` required with a fail-fast startup guard that rejects known-default values (vuln-0001, vuln-0008).
3. Add per-binding HMAC signature verification (mirror the WhatsApp route's `x-hub-signature-256` check) to `POST /api/im/webhook/:bindingId`, and return indistinguishable 401/404 responses to remove the enumeration oracle (vuln-0007).
4. Require authentication on `/ws/executions` and verify the execution's organization ownership at subscribe time (vuln-0010).

**Short-term**
5. Add `organization_id` binding to `agent_permissions` lookups and validate `:permId` mutations against the requesting org (vuln-0004).
6. Bind secondary IDs (`membershipId`, thread IDs) to the authorized parent scope before mutation, and make `requireScopeAccess` fail closed when the route inherently targets a scope (vuln-0002).
7. Add `user_id` filters to chat session and history reads (vuln-0006).
8. Upgrade `fastify`, `js-yaml`, and `nodemailer` in the backend (vuln-0013/0009/0012); run `npm audit fix` and retest.

**Medium-term**
9. Remove the `?token=` query-parameter auth path; issue short-lived, single-purpose tokens for embedded content instead (vuln-0005).
10. Complete the deferred coverage: frontend `xlsx` import reachability, agentcore/app-hosting PoC manifest CVEs (notably a critical `proxy-addr` advisory), and agent-side tool permission review, which bounds the impact of vuln-0007.

**Retest & validation:** after remediation, re-run the local PoC suites added during this assessment (`tests/unit/auth-forgery.poc.test.ts`, `tests/unit/tenant-isolation.audit.test.ts`, `tests/unit/im-webhook-auth.poc.test.ts`) — each should fail closed against the patched code — and repeat the static secret scan to confirm no default-value secrets remain.

