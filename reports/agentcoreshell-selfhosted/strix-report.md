# Security Penetration Test Report

**Generated:** 2026-11-20 06:00:18 UTC

# Executive Summary

A source-code security assessment of the **AgentcoreShell** repository (7 files, commit `3b4cc2689a1ed1d98383b0b7efdbe99fa8ea3845`) identified **one defensible trust-boundary violation**: unescaped interpolation of the `task` parameter into shell command strings in `coding_workflow.py`, enabling shell command injection on the AgentCore runtime whenever a task string under attacker influence reaches the workflow. The finding was reproduced harmlessly (marker-file PoC) with fully mocked AWS clients and fake `git`/`npm` binaries in temporary directories; no AWS APIs or deployed targets were contacted, and no source files were modified.

**Overall risk posture:** Low as shipped; medium-to-high the moment the workflow is wired to an untrusted task source.

**Key finding**
- Shell command injection via `task` in `coding_workflow.py` (High, CVSS 7.8) — four interpolation sites build `/bin/bash -c "..."` strings from a value that the function's design (a JIRA-style ticket identifier) invites sourcing externally.

**Business impact**
- If integrated with a ticketing system, webhook, or LLM-driven pipeline, a ticket title containing a double quote plus shell metacharacters yields arbitrary command execution inside the runtime container, with access to the `/workspace` checkout it operates on and the session's privileges.

**Honest scoping:** In this exact commit, `task` originates only from the operator's command line (`sys.argv[1]`), and commands an authorized shell user intentionally supplies are not treated as vulnerabilities. The reported issue is therefore a latent injection at a real trust boundary — not unauthenticated remote code execution — and its severity is contingent on the (design-implied, not yet present) wiring of `task` to an untrusted source.

# Methodology

**Engagement type:** White-box source-code security assessment of a single local repository.

**Scope:** All seven files in `/workspace/AgentcoreShell` at commit `3b4cc2689a1ed1d98383b0b7efdbe99fa8ea3845` — `shell_client.py`, `interactive.py`, `demo.py`, `coding_workflow.py`, `config.py`, `README.md`, `requirements.txt`, plus a review of the committed `__pycache__` artifacts for divergence from source (none found).

**Approach:** Full manual read of every file; verification of the boto3 API usage against the bundled botocore service model (offline — shapes inspected locally, no AWS call made); static review of all input sources and sinks; construction of a trust-boundary map distinguishing operator-supplied input (trusted per engagement rules) from latent untrusted-input paths.

**Validation:** Two independent reproductions (root agent and one dedicated validation agent, per the delegation limit) using a stubbed boto3 client, a fake `PATH` with stub `git`/`npm`/`npx` binaries, and temporary directories. A negative control (benign `JIRA-1234` task) confirmed the workflow behaves normally absent a malicious payload. Three remediation directions were each validated to block the payload.

**Constraints honored:** No AWS API invocation, no use of the configured runtime ARN, no network contact, no `npm install`, no git push, no modification of target source files.

# Technical Analysis

**Finding: Shell command injection via unescaped `task` interpolation (`coding_workflow.py`, High / CVSS 7.8, filed as vuln-0001)**

`coding_workflow()` builds shell commands by f-string interpolation of `task` and its derived `branch` name into `/bin/bash -c "..."` strings with no escaping, quoting, or validation, at four sites: the branch-name construction (line 81), `git checkout -b` (line 83), `git commit -m 'Fix {task}'` (line 86), and `git push origin {branch}` (line 89). The commands are forwarded verbatim by `AgentCoreShell.run()` as the `command` body of `invoke_agent_runtime_command`, and the runtime executes the string through `/bin/bash -c`. A double quote in `task` closes the quoted segment and the remainder is parsed as fresh shell syntax; a single quote additionally escapes the `git commit -m '...'` argument. Both independent reproductions created a harmless marker file via the injected `; : > <path>` builtin.

**Candidates examined and cleared**
- `shell_client.py` — the dict passed as `body` was verified correct against the botocore service model (`InvokeAgentRuntimeCommand.body` is a required structure with members `command`/`timeout`); `InvokeAgentRuntime.payload` is a blob and is correctly passed as encoded JSON. Response parsing has no dangerous sink.
- `interactive.py` — the `f'/bin/bash -c "{cmd}"'` framing is a reliability bug (commands containing double quotes are misparsed), not a trust-boundary violation: the only input source is the authorized operator's prompt, and intended execution of operator-supplied commands is out of scope by engagement rules.
- `demo.py` — all commands are static literals; nothing variable reaches `shell.run()`.
- `config.py` — contains a runtime ARN, region, and session UUID: identifiers, not credentials, and so not reported per engagement rules. Hygiene note only.
- `README.md` — documents `file_transfer.py`, which does not exist in this commit (docs drift, reliability note).
- `requirements.txt` — a floating floor (`boto3>=1.35.0`), no lockfile; nothing to assess.
- `coding_workflow.py` line 34 — `task` also reaches the reasoning prompt for `invoke_agent`, a prompt-injection surface only if ticket content is forwarded; not reachable in this commit and noted as forward-looking hardening.

**Systemic theme:** the local-to-runtime boundary (`shell_client.run`) executes strings verbatim by design, so every caller is responsible for treating interpolated values as untrusted data. `coding_workflow.py` is the one caller that composes commands from a value designed to be sourced externally.

# Recommendations

**Immediate**
1. Stop building shell strings in `coding_workflow.py`: pass commands as argument lists (or have the runtime accept `argv`) so no shell metacharacter interpretation occurs, and derive the branch name and commit message from a validated identifier rather than the raw task string.

**Short-term**
2. Add defense-in-depth at the `task` boundary: validate against a strict allowlist (for example `^[A-Z][A-Z0-9]*-[0-9]+$` for ticket-style identifiers) and reject anything else before interpolation; if free-form text must be supported, apply `shlex.quote()` to every interpolated value. Both approaches were validated to block the demonstrated payload while leaving benign task identifiers working.
3. If ticket content is ever forwarded to `shell.invoke_agent`, sanitize or bound it there as well to avoid pairing this with prompt injection.

**Medium-term**
4. Establish a repo convention that any value crossing into a `shell.run()` call is either a static literal or explicitly validated — `interactive.py`'s double-quote framing is a correctness bug worth fixing at the same time, even though it is operator-input-only today.
5. Resolve the documentation drift (`README.md` references `file_transfer.py`, which does not exist) and prefer environment configuration over the in-source runtime ARN.

**Retest & validation:** re-run the mocked PoC (available in the filed report) after remediation with both the malicious payload and the benign `JIRA-1234` control — the former must fail to create the marker and the latter must keep the workflow functioning end to end.

