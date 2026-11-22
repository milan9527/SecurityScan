# Security Penetration Test Report

**Generated:** 2026-11-20 13:47:57 UTC

# Executive Summary

An authorized white-box security assessment of the **AgentCore Demo Platform / Super Agent** repository identified **11 validated vulnerabilities: 2 critical, 6 high, 3 medium**, spanning agent tool-execution boundaries, workspace/skill provisioning, and multi-tenant API authorization. Overall risk posture is **critical**: both agent runtimes execute tool calls (shell, file write, web fetch) with all approvals disabled, so any prompt or retrieved content that influences the agent can result in unapproved command execution on the host or container — demonstrated locally with harmless marker operations. Separately, a systemic tenant-isolation gap allows an authenticated user of one organization to read, modify, or delete another organization's knowledge bases, group memberships, and access grants. Business impact: full host/container compromise via the agent path, and cross-tenant exposure of knowledge-base content and access control. All findings were validated locally (unit harnesses with mocked Prisma, marker files) without contacting any deployed endpoint or cloud resource.

**Key findings**
- Critical: backend Claude runtime runs with hardcoded `bypassPermissions`; the only guard is a 7-regex denylist that was bypassed, creating a marker file via `python3 -c`.
- Critical: AgentCore container runtime registers no tool-use security hook at all — every Bash/Write/WebFetch call executes unfiltered, with persistence via S3 sync.
- High: cross-tenant IDOR families on knowledge-base, userGroups, scopeMemberships, businessScopes plugin/MCP, and support-group routes; path traversal plus git argument injection in plugin installation enabling command execution.
- Medium: skill-name path traversal in workspace provisioning, zip-slip in archive extraction fallback, and cross-tenant briefing access.

**Overarching remediation theme**: enforce an approval-capable permission mode on both agent runtimes, and make organization scoping a repository-level invariant rather than a per-route convention.

# Methodology

Conducted as a **white-box, local-only source-code assessment** per OWASP WSTG and the agentic-system security guidance, with static tracing plus dynamic local validation.

**Scope**: `super-agent/backend` (Fastify + Prisma, ~67k lines), `super-agent/agentcore` (agent runtime container), and shared services. Frontend static assets and CDK infra were reviewed only as context. No deployed endpoints, credentials, or cloud resources were contacted; validation used local unit harnesses with mocked Prisma/S3 and harmless marker operations.

**Activities**:
- Shared threat model established up front and corrected as findings landed (tenant boundaries, agent tool-approval boundary, skill/plugin installation flows).
- Agent-execution boundary audit: traced chat message → agent run → tool call on both runtimes; imported the real permission-hook code and demonstrated bypass with marker files.
- Workspace/skill/plugin installation audit: traced user-controlled names, URLs, refs, and archive members through path joins, `cp`, and `git clone`; confirmed traversal and argument injection locally.
- Authorization sweep of all 49 route files: verified authentication coverage and handler-level organization scoping; confirmed cross-tenant IDORs with local PoC tests (vitest-style harness with faithful repository mocks).

**Coverage**: 19 recorded coverage entries across route families, runtimes, and provisioning paths; verified-clean families closed with named enforcing controls. Honest gaps remain on a minority of peripheral route files (spot-checked only) and on LLM-layer prompt-injection reachability, which requires a live model.

# Technical Analysis

**Severity model**: exploitability × demonstrated impact; every non-None CVSS impact metric maps to a locally demonstrated consequence.

1. **Unapproved agent tool execution — both runtimes (Critical)**. `claude-agent.service.ts` hardcodes `permissionMode: 'bypassPermissions'` with Bash/Write/Edit/WebFetch enabled; the sole guard, `dangerousCommandBlocker`, is a small regex denylist — `python3 -c` marker writes pass it, and the Write-tool path containment uses un-normalized `startsWith(cwd)`. The AgentCore `agent-runner.ts` repeats the bypass and registers no security hook at all, with S3 persistence of agent-written files back to the tenant workspace. Because untrusted content (RAG results, S3-restored skills, fetched web pages) flows into the same prompt, indirect prompt injection now has a confirmed consequence boundary crossing, not a hypothetical one.
2. **Systemic tenant-isolation gaps (High/Medium)**. Knowledge-base, briefing, userGroups, scopeMemberships, businessScopes plugin/MCP, and support-group routes query by bare record ID without `organization_id` scoping, while sibling services (credential vault, connectors, apiKeys, MCP, chat rooms, documents) demonstrate the correct pattern. This is a consistency failure, not a missing capability: the fix is to make org scoping a repository-level invariant.
3. **Workspace provisioning traversal (High/Medium)**. Plugin and skill names, git URLs/refs, and archive members flow unvalidated into `path.join`, `cp`, `git clone`, and `python3 -m zipfile` extraction. Confirmed outcomes include git clone outside the workspace, `--upload-pack` argv injection (command execution), out-of-root SKILL.md writes, and zip-slip. The codebase already contains the correct containment pattern (`deleteWorkspaceSkill`'s `startsWith` guard) — it was simply not applied to the write paths.

**Systemic themes**: approval enforcement is hardcoded off rather than configurable; authorization is enforced per-route by convention rather than by a deny-by-default data-access layer; path handling lacks a single canonical containment helper.

# Recommendations

**Immediate**
1. Remove the hardcoded `bypassPermissions` / `allowDangerouslySkipPermissions` on both runtimes (`claude-agent.service.ts`, `agentcore/src/agent-runner.ts`); default to an approval-enforcing permission mode, and restrict the Bash tool to an allowlist. Port the PreToolUse guard chain into the AgentCore runner.
2. Add `organization_id` scoping to all knowledge-base, RAG search/index, userGroups, scopeMemberships, businessScopes plugin/MCP, and support-group queries — follow the existing pattern in `credential-vault.repository.ts`.
3. Validate plugin/skill names against a strict allowlist (reject `..`, leading `-`, absolute paths) in `installPlugins` and `downloadSkill`; reject git URLs and refs beginning with `-`; enforce canonical-path containment on every workspace write, mirroring the `deleteWorkspaceSkill` guard.

**Short-term**
4. Replace the `python3 -m zipfile` extraction fallback with a member-path-sanitizing extractor.
5. Reduce the blast radius of credentials injected into the agent subprocess environment (read-only, minimal-scope tokens).
6. Introduce a repository-level tenant-scoping invariant (base repository requiring `organization_id` on object lookups) so per-route convention can no longer omit it.

**Medium-term**
7. Add regression tests reproducing each filed PoC (hook bypass, traversal writes, cross-org queries) to prevent reintroduction.

**Retest & validation**: re-run the local PoC harnesses after remediation — the marker-file tests, cross-org query tests, and extraction tests should all fail closed. Coverage gaps to close on a follow-up pass: handler-level org scoping on a2a/openapi/llm-proxy/widget/token-usage/schedules/webhooks/audit/agentPermissions routes, and LLM-layer injection reachability once a live model is in scope.

