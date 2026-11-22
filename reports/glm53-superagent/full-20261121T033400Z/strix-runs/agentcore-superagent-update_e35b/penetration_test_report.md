# Security Penetration Test Report

**Generated:** 2026-11-21 04:15:02 UTC

# Executive Summary

A comprehensive white-box security assessment of the **Super Agent platform** (Fastify + Prisma backend, AgentCore runtime, AWS CDK infrastructure) identified **29 vulnerabilities: 6 critical, 6 high, 13 medium, 3 low, 1 informational**. All validation was performed in isolation with local mocks and unit-level PoCs; no deployed endpoints were contacted.

**Overall risk posture: Critical.**

**Key findings**
- **Unauthenticated takeover paths**: internal service tokens are HMAC-signed with the public Cognito user pool ID (vuln-0001); the local-mode JWT secret has a hardcoded default with no production guard (vuln-0002); default admin credentials (`admin@example.com` / `Admin1234!`) are baked into production deploy scripts and public documentation (vuln-0005), with no login rate limiting (vuln-0003).
- **Member-reachable host command execution**: any org member can register a stdio MCP server whose command/args/env spawn on the backend host (vuln-0015); the agent runtime runs with `bypassPermissions` and a trivially bypassable regex shell denylist, reachable via prompt injection through IM/chat content (vuln-0017).
- **Broken tenant isolation in specific services**: knowledge bases (vuln-0016), business-scope memberships/plugins/connectors (vuln-0018), workflow checkpoints/executions (vuln-0019), and chat-room leader assignment (vuln-0025) all operate by primary key without organization scoping.
- **Public input surfaces without verification**: the `/ws/executions` WebSocket gateway has no authentication or ownership checks (vuln-0020); the public webhook trigger never verifies its stored secret (vuln-0011); IM adapter signature verification fails open when secrets are unconfigured (vuln-0026).

**Business impact**: on a deployment using the supplied defaults, an unauthenticated internet attacker can assume admin identity and execute commands on the backend host; authenticated members of any tenant can execute commands on the host and read or modify other tenants' data (knowledge bases, scope roles, workflow approvals, execution streams). Database and AI-agent workloads hold org-scoped business content and platform credentials, so cross-tenant access is a data-confidentiality and integrity event.

**Remediation theme**: enforce secret management (no default secrets, no public values as HMAC keys), scope every tenant query by organization, authenticate and authorize every transport including WebSockets and webhooks, and replace the bypassPermissions + denylist runtime posture with allowlist-based tool authority.

# Methodology

**Framework**: OWASP WSTG-aligned, extended with source-aware white-box techniques.

**Engagement type**: authorized white-box source-code assessment of the local repository, performed fully in isolation (local services, synthetic data, mocks only; no deployed endpoints, no real credentials, no cloud resource changes; `.git` read-only; validation artifacts confined to temporary directories).

**Scope**: `super-agent/backend` (~67k LoC TypeScript, 50 route files, 110+ services), `super-agent/frontend`, `super-agent/agentcore` runtime container, `super-agent/infra` (AWS CDK), deployment scripts and documentation, and the static `demo/` site.

**Approach**:
1. Repository mapping and trust-boundary identification; shared threat model derived and maintained for all agents.
2. Parallel specialist reviews: authentication/JWT/internal signatures; tenant ownership and authorization (IDOR/BOLA/mass assignment); SSRF/webhooks/integrations/proxies; filesystem/archive/command execution; WebSockets/SSE/injection/secret handling/dependencies; tool dispatch/MCP/agent runtime trust/workflow business logic; infrastructure and deployment configuration.
3. Each candidate traced through actual guards to sinks with file:line references; harmless local PoCs or mock-based regression tests executed against the real modules where feasible.
4. Open items from each review were re-dispatched to dedicated validation agents; all 68 coverage rows were closed with explicit outcomes (reported / ruled out with named controls / no issue found / not applicable), leaving zero unresolved rows.
5. Attack-chaining considered across confirmed findings (e.g. unauthenticated webhook → workflow api_call SSRF; default credentials → member role → stdio MCP RCE); overlapping chains were folded into the underlying findings rather than double-reported.

**Validation constraints**: PoCs were unit- or mock-level in an isolated environment. They demonstrate the missing control at the code path level; they do not by themselves prove production exploitability, which depends on deployment configuration (auth mode, environment variables, bound integrations).

# Technical Analysis

**Findings by severity** (each with file:line references, prerequisites, PoC, and remediation in its individual report):

**Critical (6)**
1. **vuln-0001** — Internal `internal.` tokens HMAC-signed with the public Cognito user pool ID (`middleware/auth.ts:79-81`); forged tokens accepted for any user/org/role, no DB checks. Offline forgery PoC.
2. **vuln-0002** — `JWT_SECRET` defaults to a hardcoded string with no production guard (`config/index.ts:30`); forged owner-role JWT accepted by `verifyLocalToken`.
3. **vuln-0003** — No rate limiting/lockout on `POST /api/auth/login` plus seeded default admin credentials.
4. **vuln-0005** — Default admin credentials hardcoded in production deploy scripts and public docs (`infra/scripts/deploy.sh:420-422`, `infra/README.md:87`).
5. **vuln-0015** — Member-configurable stdio MCP servers: command/args/env flow unvalidated into the SDK spawn config → host command execution (`mcp.routes.ts`, `claude-agent.service.ts:577-617`).
6. **vuln-0017** — Agent runtime `permissionMode: bypassPermissions` with a 5-regex shell denylist (`claude-agent.service.ts:219,419-437`, `claude-hooks.ts:53-70`); six bypasses demonstrated; untrusted IM content reaches the prompt.

**High (6)**
7. **vuln-0013** — Skill names joined into filesystem paths without containment (`workspace-manager.ts:969,1360`) → arbitrary file write with attacker content; PoC wrote outside the workspace base.
8. **vuln-0014** — Same name interpolated into `mkdir -p .../${name}` shell commands in AgentCore containers (`skill-marketplace.routes.ts:158`, `enterprise-skill.service.ts:338`); `shellEscape` does not handle `;`/`$()`/backticks.
9. **vuln-0016** — Knowledge-base service operations keyed by primary key with no organization scoping (`knowledge-base.service.ts:69-124,277-302`) → cross-tenant read/rename/delete/file deletion.
10. **vuln-0018** — Scope membership role escalation/removal cross-tenant; raw-SQL plugin/MCP listings and connector bindings missing access checks (`scopeMembership.repository.ts:86-98`, `businessScopes.routes.ts:815-953`).
11. **vuln-0020** — `/ws/executions` WebSocket: no authentication on upgrade, no ownership check on subscribe → any client receives any tenant's execution events including node outputs.
12. **vuln-0029** — Archive symlink members survive `unzip -o` and are dereferenced by `fs.cp` without `verbatimSymlinks` (`skill-marketplace.service.ts:800,843`) → out-of-bounds file read into skill storage; PoC-verified.

**Medium (13)** — Cognito unverified-email account takeover on first-login binding (vuln-0006); CORS wildcard + credentials (vuln-0007); unrestricted SSRF in workflow `api_call` nodes (vuln-0009) and MCP test endpoint (vuln-0010); webhook secret generated but never verified plus public execution-status disclosure (vuln-0011); checkpoint/execution routes missing org scoping (vuln-0019); fastify 5.6.2 CVE family (vuln-0021); axios 1.13.6 via IM SDKs (vuln-0022); js-yaml DoS via uploaded API specs (vuln-0023); cross-tenant chat-room leader manipulation (vuln-0025); IM webhook signature verification fails open → unauthenticated agent message injection (vuln-0026); plaintext IM signing secrets returned to any org member (vuln-0027).

**Low/Info (4)** — `?token=` query auth leaking into logs (vuln-0004); OAuth secrets under hardcoded default encryption key (vuln-0012); output-sanitizer redaction gaps (vuln-0024); scheduler double-execution race (vuln-0028); A2A raw-vs-hash key compare — reliability defect with pass-the-hash property (vuln-0008).

**Systemic root causes**
- **Secrets**: hardcoded defaults everywhere they matter (JWT, internal token, connector encryption, admin password) with no fail-closed guard in production.
- **Tenant scoping drift**: the `BaseRepository` pattern correctly enforces `organization_id`, but every high/medium IDOR came from raw Prisma or raw SQL calls outside that base — no lint/CI rule prevents the drift.
- **Unvalidated identity strings**: one root cause (skill name never validated) produced three distinct findings (path write, shell injection, S3 prefix escape).
- **Public transports unauthenticated**: WebSockets, webhooks, and IM callbacks lack the auth hook discipline that REST routes follow.
- **Agent authority**: the runtime grants the model full Bash/Write/WebFetch with only a denylist compensating control.

**Verified clean areas**: core repositories via BaseRepository (tasks, chat, documents, agents, connectors, organizations, projects), SSE endpoints, frontend rendering (no `dangerouslySetInnerHTML` on unescaped content, markdown without raw HTML), all Prisma raw SQL (parameterized), credential vault API responses (encrypted fields stripped), CDK resources (S3 BLOCK_ALL, encrypted RDS non-public, restricted SGs), agentcore/backend Dockerfiles (non-root), API-key service (SHA-256 hashed, expiry, rate limited).

# Recommendations

**Immediate (critical exposure)**
1. Replace the `INTERNAL_TOKEN_SECRET` derivation with a dedicated random secret from the environment; reject the Cognito pool ID and any known-default value at startup (`middleware/auth.ts`).
2. Make `JWT_SECRET` (and `INSFORGE_JWT_SECRET`, `CONNECTOR_ENCRYPTION_KEY`) mandatory with a minimum length; refuse to start in production on default or `CHANGE_ME` values (`config/index.ts`).
3. Remove default admin credentials from deploy scripts and docs; generate a random password at deploy time or force first-login rotation; add login rate limiting/lockout (`infra/scripts/deploy.sh`, `auth.routes.ts`).
4. Gate MCP server create/update (and scope attach) behind admin role and add a stdio command allowlist — closes the member-reachable host RCE (`mcp.routes.ts`).

**Short-term (high)**
5. Validate skill names to `^[A-Za-z0-9._-]+$` at every creation path, add containment checks at the filesystem `join`/`cp` sinks, pass `verbatimSymlinks: true` (or reject symlink members at ingest), and replace raw `mkdir -p .../${name}` shell calls with a file-write helper.
6. Add `organization_id` predicates to knowledge-base, scope-membership, checkpoint/execution, and chat-room-leader paths; add a CI/lint rule forbidding direct Prisma `update`/`delete`/`findUnique` on tenant tables outside `BaseRepository`.
7. Authenticate the `/ws/executions` upgrade (JWT) and enforce org-scoped subscribe checks.
8. Rework the agent runtime away from `bypassPermissions` toward allowlisted tools, and add human confirmation for IM-triggered destructive actions.

**Medium-term**
9. Introduce a single URL-validation utility (deny loopback/link-local/RFC1918/metadata, pin scheme, manual redirects, DNS pinning) and apply it to every user-URL fetch: workflow `api_call`, MCP test, a2a-client.
10. Make all IM adapter `verifyRequest` implementations fail closed when secrets are unconfigured; use timing-safe compares; verify webhook secrets (timing-safe HMAC) on the public trigger; redact secret-bearing keys from `binding.config` in admin API responses.
11. Upgrade fastify, axios (via overrides), and js-yaml to fixed versions; extend the output-sanitizer patterns (Bearer tokens, connection strings, generic API keys, Windows paths).
12. Make the workflow scheduler claim atomic (conditional `next_run_at` update or `FOR UPDATE SKIP LOCKED`); fix the A2A key comparison to hash the presented token.

**Retest and validation guidance**: after remediation, re-run the mock-based PoCs in each report (they exercise the real code paths) and add regression tests for: internal-token rejection of public-secret signatures, JWT secret startup guard, skill-name validation, org predicates on the flagged repositories, WS upgrade auth, and webhook secret verification. Confirm deployed Cognito pool settings (email verification/uniqueness) to close out the conditional account-takeover finding (vuln-0006). Note again: local reproductions demonstrate missing controls, not production exploitability — final verification should occur against a staging deployment with production-representative configuration.

