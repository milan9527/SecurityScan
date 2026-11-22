# Security Penetration Test Report

**Generated:** 2026-11-21 09:56:36 UTC

# Executive Summary

An authorized white-box source-code security assessment of the **AgentcoreShell** repository — a small Python demo client for the Amazon Bedrock AgentCore `InvokeAgentRuntimeCommand` API — identified one high-severity vulnerability and otherwise found a clean static posture.

**Overall risk posture:** Low-to-moderate. This is operator tooling, not a network-facing service, which limits exposure.

**Key finding**
- **Shell command injection via JIRA task ID** in `coding_workflow.py`: the `sys.argv[1]` task ID is interpolated unquoted into `/bin/bash -c` command strings for git checkout/commit/push, which execute on the remote AgentCore Runtime host. A task ID containing `;`, quotes, or a `--receive-pack=` payload executes arbitrary commands on the runtime host (demonstrated locally with a harmless marker-file PoC and a stubbed AWS client — no deployed endpoints were contacted).

**Business impact**
- Arbitrary command execution on the AgentCore Runtime host, inheriting the runtime's working directory and ambient IAM credentials, if task IDs ever reach the script from a ticket field, webhook, or automated trigger.

**Clean areas**
- No hardcoded credentials (the committed AWS ARN is an identifier, not a secret); no known-CVE dependencies; no misconfigurations; no other injection patterns across the codebase. Requested assessment areas with no corresponding surface (WebSockets, JWT, tenant authorization, uploads, webhooks, SSRF, archive paths) were verified absent from this repository.

# Methodology

Conducted as a **white-box, source-only assessment** with local PoC validation, per OWASP WSTG-style review adapted to a CLI tool.

**Scope:** `/workspace/AgentcoreShell` — 5 Python files (~370 lines), README, `requirements.txt`, single-commit git history. No deployed endpoints were contacted; validation used isolated local mocks (stubbed `boto3`), synthetic data, and scratch directories only. Repository source files were preserved unmodified.

**Activities**
- Full source read and trust-boundary mapping; shared threat model established before testing (operator terminal → local process → AWS AgentCore runtime; LLM output → shell/git; runtime → code-under-test supply chain).
- Baseline static coverage bundle: `opengrep` (full ruleset, intrafile taint), `ast-grep` structural pass over all Python files, `gitleaks` (worktree + history) and `trufflehog` secret detection, `trivy fs` (vuln + misconfig).
- Targeted dynamic validation of the command-injection candidate using a stubbed runtime client executing the exact command strings the real client would send.

**Out of scope / not present:** WebSockets, JWT/internal signatures, tenant ownership, uploads, webhooks, URL fetching/SSRF, and archive handling — verified not to exist in this repository and recorded as not applicable.

# Technical Analysis

**Severity model** reflects exploitability × demonstrated impact.

**Demonstrated vulnerability (high, CVSS 8.8 — AV:L/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H)**
1. **Shell command injection via task ID** — `coding_workflow.py` takes `task` from `sys.argv[1]`, builds `branch = f"fix/{task.lower()}"`, and interpolates it unquoted into `bash -c` strings at the `git checkout -b`, `git commit -m`, and `git push origin` steps, which run on the AgentCore Runtime host via `InvokeAgentRuntimeCommand`. Locally demonstrated: a `;` payload escapes quoting in both the checkout and push sinks and in the single-quoted commit message; a `--receive-pack=` payload makes `git push` treat the branch token as the `<repository>` operand and spawn an attacker-named program as remote helper. No validation, allowlist, escaping, or `--` end-of-options guard exists anywhere on the path (CWE-78).

**Systemic themes**
- Shell-string assembly for remote execution with no input quoting discipline — the single root cause behind the finding.
- Reliance on ambient IAM credentials with no least-scoping guidance in the demo.

**Assessed and cleared**
- `interactive.py` REPL quote-breaking: ruled out — arbitrary command execution on the runtime is the product's intended operation for the local operator.
- Hardcoded AWS account ID / runtime ARN in `config.py`: informational hygiene, not a credential; recommend env-only configuration.
- `boto3>=1.35.0` unpinned floor: reproducibility hygiene; no advisory-matched vulnerable version (no lockfile).
- Static taint and structural scans: zero findings beyond the above.

**Honest limitations**
- The injection PoC was reproduced locally with a stubbed client; a local reproduction does not by itself prove production exploitability on a deployed AgentCore runtime. Severity is contingent on how task IDs reach the script in practice (unverified deployment context).

# Recommendations

**Immediate**
1. Fix the command injection in `coding_workflow.py`: validate the task ID against a strict allowlist (e.g. `^[A-Z]+-\d+$`) and stop interpolating it into `bash -c` strings — pass the branch name to git as a discrete argument with a `--` end-of-options separator, or use `shlex.quote()` (noting `shlex.quote` alone does not prevent git-option interpretation).

**Short-term**
2. Move the default AgentCore runtime ARN out of source into environment-only configuration, and purge it from git history if the account ID is considered sensitive.
3. Pin `boto3` to an exact version or add a lockfile for reproducible dependency scanning.
4. If this script is ever wired to an automated trigger (ticket webhook, queue consumer, CI parameter), treat the injection as remotely triggerable and prioritize accordingly — that deployment context is outside this repository and was not verified.

**Retest & validation**
- Re-run the local PoC (stubbed client, task IDs `x; touch /tmp/pwned #` and `--receive-pack=...`) after remediation: the marker file must not be created and git must reject the branch token, while a legitimate task ID (e.g. `JIRA-1234`) still completes the workflow.

