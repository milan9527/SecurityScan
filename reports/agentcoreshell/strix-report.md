# Security Penetration Test Report

**Generated:** 2026-11-20 03:06:59 UTC

# Executive Summary

A source-code security assessment of the **AgentcoreShell** repository (commit `3b4cc26`) — a 7-file client-side demo for Amazon Bedrock AgentCore Runtime's `InvokeAgentRuntimeCommand` API — identified one validated trust-boundary violation and a set of reliability/hygiene items. No critical or high-severity issues were found.

**Overall risk posture:** Low, with one conditional medium-class weakness that owners should fix before any integration work.

**Key finding**
- **Shell command injection via the unvalidated `task` parameter in `coding_workflow.py`** (filed as report `vuln-0001`, Low/3.7, CWE-78, high confidence). The ticket string is interpolated unescaped into three runtime shell commands (`git checkout -b`, `git commit -m`, `git push`); a proof of concept proved that plain metacharacters (`;`, `$(...)`) — no quote characters needed — execute attacker-chosen commands inside the runtime workspace, and that the workflow's own `git add -A` + push then swept the injected file into the commit and onto the pushed branch. **Prerequisite, stated plainly:** as committed, `task` comes only from `sys.argv[1]` typed by the authorized operator, so this is not unauthenticated remote code execution today; it becomes exploitable the moment an integration sources the task string from untrusted input (ticketing system, HTTP API, LLM output). Severity reflects that honest, conditional exposure.

**Business impact**
- If an integrator wires `task` to untrusted input, an attacker gains arbitrary command execution inside the AgentCore Runtime session with the session's privileges, plus unauthorized commits pushed to the operator's repository.
- The demo currently poses no network-exposed risk: nothing in it listens on a port, and no AWS APIs, npm installs, or pushes were performed during testing.

**Remediation theme:** validate external identifiers at the boundary and stop building shell commands by string interpolation; gate the automated `git add -A` + push behind review.

# Methodology

**Engagement type:** White-box source-code assessment of a local repository, with fully local dynamic validation using mocked cloud clients — no deployed target.

**Scope:** All seven files at commit `3b4cc26`: `README.md`, `requirements.txt`, `config.py`, `shell_client.py`, `interactive.py`, `demo.py`, `coding_workflow.py`. Target source files were preserved unmodified; all PoC artifacts were created outside the repository.

**Constraints honored:** No AWS API calls or contact with the configured runtime ARN; no git pushes outside a local sandbox bare repo; no `npm install`; validation used a recording fake `boto3`, stub `npm`/`npx`, and real local `/bin/bash` and git in disposable temporary directories. Commands explicitly supplied by the authorized shell user were treated as intended behavior, not vulnerabilities.

**Activities:** full read of all seven files; trust-boundary and data-flow mapping (task parameter → shell commands → runtime session; operator stdin → runtime; env vars → boto3 client); one delegated validation agent that captured the exact command strings the real workflow submits and replayed them with real shell/git semantics (24/24 assertions, control run for contrast); bounded static hygiene passes (gitleaks secrets scan, trivy filesystem vuln/misconfig scan, opengrep taint-mode pass with bundled rules, and a structural AST pass). Per engagement rules, the ARN and account ID in `config.py` were treated as identifiers, not credentials, and were not reported as secret exposure.

# Technical Analysis

**Confirmed finding**
1. **Shell command injection via `task` in `coding_workflow.py` (Low/3.7, CWE-78, report `vuln-0001`)** — `branch = f"fix/{task.lower()}"` and three `shell.run(f'/bin/bash -c "...git... {branch|task}..."')` calls at lines 81-90 interpolate the raw ticket string with no validation or escaping anywhere on the path. `task.lower()` neutralizes no metacharacters. Because the string crosses two shell parsing layers (the runtime session shell, then the inner `/bin/bash -c`), plain metacharacters suffice: `task = "JIRA-1234; touch pwned_marker"` executed the marker command inside the runtime workspace at sinks 83 and 89 (the legitimate `git checkout` still exited 0), `$(...)` executed at the session-shell layer, and a single quote broke out of the commit-message quoting at sink 86. The proof of concept replayed the exact captured command strings with real `/bin/bash` and real git and demonstrated the injected file being committed by the workflow's own `git add -A` and present on the pushed branch in a local bare remote, against a clean control run. Prerequisite: `task` must originate from untrusted input; the shipped entry point (`sys.argv[1]`) is the authorized operator.

**Open item (needs owner verification, not locally validatable)**
- The `npm install → npm test → reasoning-prompt feedback → git push` chain trusts third-party package install scripts and unreviewed workspace content, then auto-pushes. The runtime agent's tool authority and network exposure could not be observed without a live AgentCore runtime (out of scope); recommend the owner confirm the reasoning agent's granted tools and egress before enabling this workflow in production.

**Reliability issues (not security findings, per engagement rules)**
- `README.md` documents a `file_transfer.py` that does not exist; its session-sharing claim is defeated by `config.py`'s per-process `uuid4()`.
- `shell_client.py:21` uses `int | None` while the README claims Python 3.9+ support (import fails on 3.9).
- `interactive.py:48` raises an unhandled IndexError on `!timeout ` with no value; `interactive.py:54`'s double-quote wrapper mangles operator commands containing `"`/`$`.
- Documented 64 KB command / 1–3600s timeout bounds (`shell_client.py:52-53`) are not enforced client-side.

**Areas tested and clean:** `demo.py` (all-literal commands, no input surface), `interactive.py` (operator-supplied commands are intended behavior), `config.py` (env-only inputs; the embedded ARN/account ID is an identifier, not a credential), `shell_client.py` (passes caller strings to the operator's own runtime; no local execution of untrusted commands), plus gitleaks (0 findings), trivy fs vuln/misconfig (0 results), opengrep taint-mode (0 findings), and a structural AST pass (no new candidates). Coverage limitations: no live AgentCore runtime behavior, IAM/ARN-side configuration, or `npm` supply-chain surfaces could be exercised; findings rest on local mock-based validation.

# Recommendations

**Immediate**
1. Validate `task` at every entry point against a strict identifier allowlist (e.g. `^[A-Za-z0-9._-]+$`) and reject anything else before it reaches a command string, prompt, or branch name.
2. Stop constructing shell commands by f-string interpolation: execute the git operations with argument-array invocation and no shell (each of `checkout -b`, `add`, `commit -m`, `push` is a fixed argv with the ticket key as one argument), or at minimum `shlex.quote` every interpolated token at all three sinks (`coding_workflow.py:83/86/89`). Derive branch names from the stored, validated ticket key.
3. Add a regression test feeding each sink a task value containing `;`, `$()`, backticks, and quote characters, asserting no second command executes.

**Short-term**
4. Replace the blind `git add -A` + push (`coding_workflow.py:84-89`) with an explicit file list and a human review gate, and check each git step's exit code so a failed checkout/commit cannot silently continue to push — this removes the impact amplifier that swept the PoC's injected file into the pushed branch.
5. Treat the task value as untrusted data in the reasoning prompt (`:34`) and the test-output feedback loop (`:61`): delimit and label it as external content rather than interpolating it into instructions.
6. Fix the reliability items: remove the `file_transfer.py` section from `README.md` (the file does not exist); correct the README's session-sharing claim (per-process `uuid4()` in `config.py` defeats it — use an env var or persisted session ID); replace the `int | None` annotation (`shell_client.py:21`) or raise the documented Python floor above 3.9; guard `interactive.py:48` against an IndexError on `!timeout` with no value; enforce or drop the documented 64 KB / 1–3600s bounds.

**Medium-term**
7. Prefer environment-only configuration defaults in `config.py` over the hardcoded ARN (identifier hygiene).
8. Remove the committed `__pycache__` artifact and add a `.gitignore`.

**Retest & validation:** re-run the supplied PoC (`poc_task_injection_compact.py`) after remediation — it must show zero injected markers for every payload while the control run still completes. For the one open follow-up (runtime-agent authority and network exposure of the `npm install → npm test → reasoning loop`), confirm in a staging AgentCore runtime what tools and egress the reasoning agent is granted before enabling auto-push in production.

