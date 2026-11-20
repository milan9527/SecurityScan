# Security Penetration Test Report

**Generated:** 2026-11-20 02:28:11 UTC

# Executive Summary

An authorized local smoke test of the disposable Python authentication fixture **`app.py`** confirmed a **SQL injection authentication bypass** in the `login()` function (filed as `vuln-0001`, Medium, CVSS 5.1, CWE-89).

**Overall risk posture:** The credential check can be defeated by any caller who can supply a username or password string; no valid credential is needed to authenticate as the seeded `demo` user.

**Key finding**
- `login()` interpolates caller-supplied credentials directly into the SQL statement text; all five tested injection payloads (tautology and comment-based, on both parameters) produced a successful login without a valid password.

**Validation quality**
- The identical malicious payloads were rejected 5/5 by the sibling `login_parameterized()` function, attributing the bypass specifically to the unsafe string interpolation.
- Ordinary logins behave correctly in both functions: valid credential accepted, wrong password and unknown user rejected.

**Business impact**
- Within this fixture, the consequence is unauthorized authentication as the sole seeded user against in-memory data. The same flaw in a production analogue would allow account takeover of arbitrary accounts without knowing any password.

**Remediation theme**
- Adopt parameterized queries everywhere credentials (or any user input) touch SQL — the safe pattern already exists in the same file. Per the owner's instruction, no code was modified.

# Methodology

Conducted as a **white-box local code review with dynamic validation**, per the owner's constraints: only the supplied disposable fixture was tested, via local Python execution — no external targets, network scanning, cloud endpoints, or credential discovery.

**Scope:** `/workspace/strix-fixture` (`app.py`), its `database()`, `login()`, and `login_parameterized()` functions. Password storage quality was out of scope per the owner.

**Approach:**
- Established a scan-wide threat model treating the two login parameters as fully attacker-controlled, with `login_parameterized()` as the intended negative control.
- Delegated validation to a single specialized SQL-injection subagent, which produced the proof-of-concept script; the root agent executed and confirmed its output after the subagent terminated unexpectedly.
- Ran a local PoC importing the unmodified fixture: baseline logins (valid, wrong password, unknown user), five injection payloads against `login()`, and the identical payloads against `login_parameterized()`.
- Captured the exact SQL statements executed by `login()` via an SQLite trace callback to document how attacker input rewrites the query structure.

**Categories tested:** SQL injection authentication bypass, authentication correctness of ordinary logins, parameterized-query control comparison. No other categories were applicable (no network surface, no third-party dependencies, no persistent data).

# Technical Analysis

**Severity model:** One dynamic finding, rated Medium (CVSS 5.1, `AV:L/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N`) — the bypass is fully confirmed and reproducible, but the fixture has no network surface, so the contextual attack vector is local. In a network-exposed deployment the same flaw would rate High/Critical.

1. **SQL injection authentication bypass in `login()`** (Medium, CWE-89) — `app.py:14` builds the query as `f"SELECT name FROM users WHERE name = '{name}' AND password = '{password}'"` with no validation, escaping, or binding. A password of `' OR '1'='1' --` renders the predicate `(name='demo' AND password='') OR ('1'='1')` and matches the seeded row; a name of `demo' --` comments out the password check entirely. All five tested payloads returned `True` with no valid credential, returning the `('demo',)` row.

**Negative control:** `login_parameterized()` (`app.py:18-23`) executes the same logical query with bound parameters and rejected all five identical payloads, confirming the root cause is the interpolation rather than the data or query shape.

**Baseline behavior:** Ordinary logins are correct in both functions — `('demo', 'fixture-password')` → `True`; wrong password and unknown user → `False`.

**Systemic root cause:** Credential values flow from function arguments into SQL statement text via string interpolation. The safe pattern already exists alongside the vulnerable one in the same file; the fix is substitution, not invention.

# Recommendations

**Immediate**
1. Replace the f-string query construction in `login()` with bound parameters, mirroring `login_parameterized()` exactly: execute the constant statement `SELECT name FROM users WHERE name = ? AND password = ?` with `(name, password)` passed as the parameter tuple. This closes the bypass completely — verified in this test, where the parameterized form rejected all malicious payloads while accepting the valid credential. Per the owner's instruction, `app.py` was not modified during this assessment; no patch is attached.

**Short-term**
2. Adopt a repository convention that user-supplied values never enter SQL via string interpolation or concatenation; any code review checklist for this codebase should flag f-string/query-building patterns on credential or request paths.
3. If this fixture pattern is derived from or destined for production code, apply the same parameterization review to every login or lookup path that handles user input before deployment.

**Retest & validation guidance**
- Retest after the change by replaying the PoC: the five payloads (`' OR '1'='1' --`, `' OR 1=1 --`, `demo' --` and variants) must return `False` from `login()`, while `('demo', 'fixture-password')` must continue to return `True`, and both functions should agree on all inputs.
