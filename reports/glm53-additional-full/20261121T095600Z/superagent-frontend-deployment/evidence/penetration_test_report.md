# Security Penetration Test Report

**Generated:** 2026-11-21 10:09:22 UTC

# Executive Summary

A deep authorized source-code security assessment was performed on the **Super Agent** multi-tenant AI-agent platform monorepo (React/Vite frontend, Fastify backend, AgentCore runtime, AWS CDK infrastructure). All validation was local-only with mocks and synthetic data; no deployed endpoints or cloud resources were contacted.

**Overall risk posture: Critical.** The platform's core trust boundaries — tenant isolation, authentication, and the workflow-execution engine — all failed validation in at least one demonstrable way.

**Key findings**
- **Authenticated remote code execution**: any ordinary organization member can execute arbitrary JavaScript on the backend server via a workflow "custom transform" node evaluated with unsandboxed `eval()` (CVSS 8.8, working local PoC).
- **Authentication forgery family**: the internal-token HMAC key is the Cognito userPoolId, which is publicly disclosed by an unauthenticated config endpoint; combined with a hard-coded default JWT secret and `?token=` query-parameter acceptance, this enables full identity forgery (CVSS 9.8, PoC-validated).
- **Cross-tenant IDOR**: knowledge-base, briefing, and scope-plugin routes perform lookups with no organization scoping — cross-org read/modify/delete of tenant content (CVSS 8.3, PoC-validated).
- **Unauthenticated abuse surfaces**: public webhook trigger (arbitrary tenant workflow execution), generic IM webhook, avatar generation, and a WebSocket gateway accepting subscriptions to any execution with no authentication.
- **Deployment secrets**: a seeded admin password (`Admin1234!`) written to deploy logs and published in docs; a hard-coded Redis password; JWT_SECRET left unset on the CI deployment path.
- **SSRF with response readback** in the workflow API-call node, and medium-severity frontend session issues (postMessage without origin validation, sandbox-nullified preview iframes, tokens in URLs).

**Business impact**: full backend compromise by any low-privilege tenant user, cross-tenant data exposure, unauthenticated resource consumption (LLM cost), and administrative takeover of freshly deployed instances. Production deployment exposure of individual findings is unverified (local-only scope) and is stated in each report's assumptions.

# Methodology

White-box source-code assessment following OWASP WSTG-aligned categories, executed as a multi-agent deep review of the complete repository.

**Scope**: the full monorepo — `frontend/` (299 files), `backend/` (250 files), `agentcore/`, `infra/` (CDK + provisioning scripts), `app-hosting/poc/`, `industry-packs/`, lockfiles, Dockerfiles, and deployment scripts. Constraints: local-only validation with mocks and synthetic data; no deployed endpoints, cloud resources, real credentials, or installation hooks; target source preserved unmodified.

**Activities**
- Shared threat model derived from repository structure before testing; corrected and finalized afterwards.
- Source-aware static triage: opengrep (taint mode), ast-grep structural pass, gitleaks + trufflehog secret detection, trivy filesystem scanning across all lockfiles.
- Full frontend mapping (pages, services, auth/session, routing) with review of rendering paths, browser storage, postMessage/WebSocket origin handling, and frontend-vs-backend authorization parity.
- Full backend mapping (50 route modules, auth middleware, authorization layers, websocket gateway, services, repositories) with per-route tenant-scoping analysis, mass-assignment, injection, and secret review.
- Infrastructure/supply-chain review: Dockerfiles, docker-compose stacks, CDK stack, EC2 user-data, deploy/CI scripts, lifecycle scripts, lockfile consistency, secret exposure, deployment defaults.
- Validation via harmless local PoCs: the RCE (marker-file eval PoC), unauthenticated WebSocket subscription, SSRF (mocked fetch), path traversal (mocked S3), and IDOR/auth-forgery reproductions all ran against the real code with mocks through the existing vitest harness.
- Per-CVE reachability analysis for known-CVE dependency findings (usable as well as exclusion traces for non-reachable ones).

**Deduplication**: one report per root cause; sibling instances grouped with individual constraints stated. Demonstrated vulnerabilities, unverified candidates, and hardening observations were explicitly distinguished throughout; local reproduction is never presented as proof of production exploitability.

# Technical Analysis

28 vulnerability reports filed (3 critical, 7 high, 9 medium, 3 low, 7 informational) across 69 recorded coverage entries (39 reported, 22 no-issue-found, 6 ruled-out, 2 needs-follow-up).

**Critical**
1. Auth forgery family — internal-token HMAC key = public Cognito userPoolId (`GET /api/auth/config` disclosure), default JWT secret fallback, `?token=` acceptance (`middleware/auth.ts`, `config/index.ts:30`).
2. Hardcoded seed admin password `Admin1234!` seeded, logged, and documented (`infra/scripts/deploy.sh:418-421`, `ci/remote-deploy.sh`).
3. PoC app-hosting stack: docker.sock mounts into two containers, insecure Traefik dashboard, hardcoded tenant JWT secrets (`app-hosting/poc`).

**High**
4. Authenticated RCE via unsandboxed `eval()` of workflow custom-transform expressions (`action-executor.ts:316-325`); any 'member' role; second same-class sink in `code-artifact-executor.ts:296` currently blocked only by an incidental SyntaxError.
5. Cross-org IDOR on knowledge-base/briefing/scope plugin/MCP-server routes — no `organization_id` scoping (`knowledge-base.service.ts`, `businessScopes.routes.ts:821,940`).
6. Unauthenticated public webhook trigger — no auth/HMAC/replay/rate limit.
7. Unauthenticated generic IM webhook processing attacker messages through victim-org agents.
8. Hardcoded Redis password + unset REDIS_PASSWORD/JWT_SECRET in provisioning scripts.
9. `ws` 8.19.0 CVE-2026-48779 memory-exhaustion DoS, reachable on the unauthenticated WebSocket gateway (dependency finding with reachability trace).

**Medium**
10. Unrestricted SSRF with response readback in workflow API-call node (`action-executor.ts:123`).
11. Unauthenticated WebSocket subscription to arbitrary execution events (`/ws/executions`, no preHandler, no ownership check).
12. Path-traversal family: pack-deploy `packId`/`scopeDirName` (authenticated file read); agentcore `workspace-sync.ts` S3-key traversal (locally confirmed path math; tenant-reachable write primitive not found); `workspace-manager.ts` sibling-prefix `startsWith` bypass.
13. Unauthenticated avatar generation/proxy endpoints.
14. agentAccess cross-org permission confusion.
15. ConnectorPanel postMessage without origin/state validation (connector credential-binding hijack).
16. Preview iframes with `allow-scripts allow-same-origin` nullifying sandbox.
17. MCP SDK CVE-2026-104850 OAuth-credential redirection (reachable).

**Low/Info**: session token in URL query strings; xlsx 0.18.5 prototype pollution + ReDoS (low reachability); six dependency CVEs filed with concrete not_reachable/not_applicable exclusion traces (axios, protobufjs, lodash, react-router, ip-address, undici).

**Systemic root causes**: (a) authorization implemented as role checks without object-level tenant scoping on several route families; (b) trust in "workflow author" as a privileged actor without sandboxing server-side code evaluation; (c) unauthenticated machine-facing endpoints (webhooks, WS, avatars) lacking signature/ownership controls; (d) deployment scripts shipping weak/default secrets.

**Ruled out (named controls)**: SQL injection (all raw SQL parameterized), files.routes S3 prefix enforcement, workflow/document org scoping, Cognito JWT verification itself, skill-marketplace SSRF (github.com hostname guard), applyFilter/applyReduce evals (unreachable), credentialed-CORS impact (Bearer auth, no cookies).

**Open proof gaps**: agentcore `process.env.AUTH_TOKEN` / workspace persistence across AgentCore container reuse (platform lifecycle not determinable from the repo); app-hosting PoC services pinned to an unpatchable fastify 4.x line.

**Attack chains considered**: member → eval RCE (standalone, already maximum impact); auth forgery → member → RCE; IDOR → workspace-file access → path traversal; sandbox-nullified iframe + token-in-URL (topology-dependent escalation documented in the relevant reports).

# Recommendations

**Immediate**
1. Remove the `eval()` in `action-executor.ts` (applyCustomTransform) and `code-artifact-executor.ts` — replace with a restricted expression evaluator (e.g. jsonata/expr-eval) or a real sandbox (isolated-vm), and gate code/transform nodes behind an admin-only permission. Fixing only one of the two sinks re-opens the other.
2. Give the internal token its own dedicated random secret (never derive it from the userPoolId), remove the default JWT_SECRET fallback (fail fast when unset), and stop accepting JWTs from the `?token=` query parameter.
3. Add `organization_id` scoping to every knowledge-base, briefing, and business-scope plugin/MCP-server lookup, following the existing pattern in `workflow.service.ts`; sweep sibling `/:id` routes in the same pass.
4. Require authentication plus HMAC signature and replay/rate protection on the public webhook trigger and the generic IM webhook; add the authenticate preHandler to the avatar and `/ws/executions` routes, and validate execution ownership on WS subscription.
5. Generate a random per-deployment admin password (no seeded default), remove it from deploy logs and documentation, and set REDIS_PASSWORD and JWT_SECRET from a secret store in all provisioning paths (including `gen-base-env.py`).

**Short-term**
6. Validate API-node and MCP-server URLs against private/link-local ranges with an org egress policy at execution time (`action-executor.ts:123`, `mcp.service.ts:283`).
7. Add origin + state-nonce validation to the ConnectorPanel OAuth message handler; drop `allow-same-origin` from preview iframes; replace token-in-URL previews with per-resource signed URLs.
8. Adopt a canonical, separator-aware path containment helper and apply it at every join with untrusted components (`workspace-sync.ts`, `resolveWorkspaceFilePath`, `readWorkspaceFileFromS3`).
9. Upgrade `ws` to ≥8.21.0, the MCP SDK to ≥1.31.0, and xlsx off the npm-frozen 0.18.5; apply the documented npm overrides for axios/protobufjs/lodash/undici/ip-address in one pass.

**Medium-term**
10. Investigate AgentCore container-reuse semantics for `AUTH_TOKEN` and workspace residue before multi-tenant production use; upgrade the app-hosting PoC services off fastify 4.x and remove docker.sock mounts and the insecure Traefik dashboard from all shipped paths.
11. Set `CORS_ORIGIN` explicitly in deployment env generation (low current impact due to Bearer auth, but removes the wildcard default).

**Retest & validation**: re-run the provided local PoC suites (workflow transform eval, WS subscription, SSRF mock, IDOR and auth-forgery tests) after remediation; all should fail closed. Confirm in a staging deployment that the member-reachable RCE and cross-org IDOR no longer reproduce, and that webhooks/WS/avatar endpoints reject unauthenticated requests.

