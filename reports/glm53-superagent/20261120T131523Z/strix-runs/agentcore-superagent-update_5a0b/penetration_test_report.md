# Security Penetration Test Report

**Generated:** 2026-11-20 13:34:06 UTC

# Executive Summary

A source-only white-box security assessment of the **Super Agent** backend (`super-agent/backend`, Fastify + Prisma + S3) focused on file and workspace boundaries identified **four confirmed vulnerabilities — three high, one medium** — each reproduced with a local PoC against the real application code, without contacting any deployed endpoint.

**Overall risk posture: Elevated.** The organization (tenant) boundary, the strongest assumed control in this platform, is missing on the knowledge-base and briefing routes: any authenticated member of any organization can read, modify, and delete another organization's knowledge bases, files, and folders, and read and mutate other organizations' briefing feeds. A second class of weakness allows filesystem paths to escape their intended directories through unsanitized identifiers (skill/agent names) and unvalidated route parameters (pack deploy).

**Key findings**
- **Cross-organization IDOR in knowledge-base routes (High, CVSS 8.8)** — read/modify/delete of other orgs' KBs, files, folders, tags, and scope bindings using bare UUIDs.
- **Cross-organization access on briefing routes (High, CVSS 7.6)** — read, mark-read, and archive other orgs' briefings with no org or scope-membership check.
- **Path traversal in workspace provisioning via skill/agent names (High, CVSS 7.6)** — names with `../` escape the workspace skills/agents directories during session provisioning, giving an authenticated user file writes outside the intended tree as the service user.
- **Path traversal in pack-deploy endpoints (Medium, CVSS 4.3)** — `packId`/`scopeDirName` route parameters reach `path.join` unvalidated, allowing authenticated users to read fixed-name files outside the industry-packs tree.

**Business impact:** cross-tenant exposure of knowledge-base content and briefing data (confidentiality and integrity), and unauthorized file writes on the backend host (integrity, potential pivot to code execution if a written file is later executed or included).

# Methodology

Gray-box (source-available) assessment of the local repository, following OWASP WSTG emphasis areas for file handling and access control. **Scope:** `super-agent/backend` routes, services, and workspace management, plus pack-deploy and avatar surfaces; testing was local-only (vitest PoCs with mocked S3/DB/auth) per engagement constraints — no deployed endpoints, real credentials, or cloud resources were touched. **Activities:** (1) full mapping of upload/download/archive/workspace/repository paths and their guards; (2) systematic static tracing of attacker-controlled inputs (filenames, IDs, scope identifiers, route params, skill/agent names) through guards to filesystem and database sinks; (3) review of existing test invariants (`workspace-manager.test.ts`, `file-storage-isolation.property.test.ts`) against actual code; (4) execution of four local PoC regression tests driving the real route handlers and services with in-memory mocks; (5) counterevidence passes on every candidate, including one candidate (zip-slip in skill extraction) that was ruled out with named controls. **Coverage:** 17 coverage entries recorded across file routes, workspace manager, knowledge-base, briefing, pack-deploy, avatar, document-group, and file-storage surfaces.

# Technical Analysis

**Severity model:** impact x exploitability, scored on the demonstrated PoC only.

1. **Knowledge-base cross-org IDOR (High)** — `knowledge-base.service.ts` methods (`findById`, `update`, `delete`, `listFiles`, `updateFile`, `deleteFile`, `batch*`, folders, tags, scope bindings) filter by primary key only; `requireModifyAccess` is a role check, not an ownership check. The listing endpoint is org-scoped, but UUIDs passed to read/mutate/delete endpoints are not. PoC: org-A member renamed and deleted org-B KB files via the real route handlers with a prisma mock mirroring production `where` clauses.

2. **Briefing cross-org access (High)** — briefing routes filter only by `business_scope_id`; an org-A user read org-B briefings, marked them read, and archived them.

3. **Skill/agent-name path traversal (High)** — skill and agent names have no format validation at creation and flow into `path.join` in `workspace-manager.ts` (`downloadSkill`, `generateAgentSubagentFiles`, `installSkillToWorkspace`, `syncSkills`) without the containment check that sibling functions (`readWorkspaceFile`, doc-group symlink naming) do apply — a contrast control proving the codebase's own hardening pattern was missed at these sinks. PoC: a `../`-containing name wrote marker files outside the workspace root during provisioning.

4. **Pack-deploy traversal (Medium)** — `packId`/`scopeDirName` are joined into filesystem paths with no containment check; the `industry-pack-` prefix is cancellable via `packId = 'a/../../'`. Impact is bounded to fixed filenames (`onboarding.json`, `scope.json`, etc.) — read-only disclosure.

**Ruled out:** zip-slip in `extractSkillZip` — `unzip` strips `../` and `python3 -m zipfile -e` sanitizes member names on modern Python; the production alpine image ships neither utility. **Confirmed sound:** S3 file/document storage enforces org-prefixed keys on every download/delete/metadata path; workspace file read/write guards consistently apply join + containment checks.

**Untested coverage (honest limits):** the S3 content-download path for knowledge-base files (`getFile` returns `s3_key`) was not validated; `bindToScope`/`unbindFromScope` cross-org binding shares the vuln-0002 root cause but was not separately PoC'd; the marketplace-install caller of `installSkillToWorkspace` was not audited end to end; the avatar proxy/presign lack ownership binding but keys are unguessable — recorded as a hardening note, not a filed finding.

# Recommendations

**Immediate**
1. Close the knowledge-base IDOR: add `organization_id` (from `request.user.orgId`) to every `where` clause in `knowledge-base.service.ts`, and enforce it in the routes. Retain `tests/unit/kb-idor.poc.test.ts` as a regression test — it will fail until isolation is added, then flip its assertions to expect 403/404.
2. Apply the same org (or scope-membership) filter to all briefing routes in `briefing.routes.ts`.
3. Validate pack identifiers at the API boundary: reject `packId`/`scopeDirName` containing `/`, `\`, or `..` (strict `^[A-Za-z0-9_-]+$` allowlist), and add a post-resolve containment check against the canonical industry-packs base directory in both `getOnboardingConfig` and `deploy`.

**Short-term**
4. Enforce a skill/agent name format (`^[A-Za-z0-9][A-Za-z0-9 _-]*$`, no path separators) at creation and update, and add the `readWorkspaceFile`-style containment check (`startsWith` on the resolved base) to `downloadSkill`, `generateAgentSubagentFiles`, `installSkillToWorkspace`, and `syncSkills` — including the `rm` cleanup path in `syncSkills`.

**Medium-term**
5. Bind knowledge-base file downloads to org-scoped S3 key validation, mirroring the pattern already used in `file.service.ts` (`validateFileAccess`), and confirm the KB `getFile` download path inherits it.
6. Add an `authenticate` preHandler to `/avatars/generate` and `/generate-batch`, and consider binding avatar keys to the owning user even though keys are unguessable.
7. Centralize tenant isolation: a repository-level enforcement point (or a Fastify `preHandler` that verifies `record.organization_id === request.user.orgId`) prevents the per-method omissions that caused both high IDORs; add unit tests for every knowledge-base and briefing method asserting cross-org requests are refused.

**Retest & validation:** re-run the four PoC tests (they are standard vitest files) after remediation — all should show the attack paths closed while legitimate same-org requests continue to succeed.

