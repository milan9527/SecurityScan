# Security Penetration Test Report

**Generated:** 2026-11-20 07:29:23 UTC

# Executive Summary

An authorized white-box audit of the local download handlers module (`app.py`) identified one confirmed security defect: the `download()` function performs no containment check on the user-supplied `filename`, permitting arbitrary file reads outside the administrator-configured download root via both relative path traversal and absolute-path injection. The finding was demonstrated with a working local proof-of-concept using synthetic data. The versioned alternative, `download_v2()`, implements a correct resolve-and-containment control and is not affected. Overall risk is assessed as medium: the defect fully breaks the module's documented trust boundary, but exploitation requires access to the `filename` parameter and knowledge of a target path.

**Key finding**
- Path traversal / arbitrary file read in `download()` (`app.py` line 7) — reported as vuln-0001, CVSS 6.5 (Medium).

**Business impact**
- Any file readable by the application process — credentials, configuration, source, other users' data — could be disclosed if the parameter is attacker-controlled.

# Methodology

**Engagement type:** White-box source review with local dynamic validation, per the supplied synthetic-test constraints (single agent, no external hosts, no application-code modification).

**Scope:** The single module `downloads/app.py`, comprising two download handlers (`download` and its versioned alternative `download_v2`).

**Approach:** Full review of every function, including the versioned alternative. The documented trust boundary (root is administrator-configured and immutable; no client symlink creation) was treated as part of the application contract and not itself tested. Each function was invoked in a local Python process with synthetic directories and files: a benign baseline request, relative-traversal and absolute-path payloads against both functions, and the guarded function as a negative control. No external hosts or cloud services were contacted.

# Technical Analysis

**Severity model** reflects demonstrated impact (arbitrary read of process-readable files) tempered by the parameter-access precondition.

1. **Path traversal / arbitrary file read in `download()`** (Medium, CVSS 6.5, AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N) — `(Path(root) / filename).read_bytes()` passes the client-controlled `filename` to the filesystem without validation. Two payload classes were demonstrated: `../../secret/flag.txt` (relative traversal) and a direct absolute path (pathlib discards the root when the right operand is absolute). Both returned the contents of a file outside the root; `download_v2()` rejected the same inputs with `PermissionError`, confirming the intended invariant exists and that `download()` fails to enforce it.

**Systemic theme:** the codebase contains both the broken and the correct implementation of the same control; the legacy `download()` path predates or bypasses the containment check that `download_v2()` applies.

# Recommendations

**Immediate**
1. Route all downloads through containment logic equivalent to `download_v2()` (resolve root and target, require `target.is_relative_to(base)` before reading), or retire the legacy `download()` function.

**Short-term**
2. Replace every caller of `download()` with `download_v2()` (or a renamed single guarded entry point), and add a unit test asserting that traversal and absolute-path payloads raise `PermissionError`.

**Retest & validation:** after remediation, re-run the proof-of-concept payloads against the fixed handler and confirm both the relative-traversal and absolute-path classes are rejected while benign filenames continue to download correctly.

