# Security Penetration Test Report

**Generated:** 2026-11-20 07:28:07 UTC

# Executive Summary

The audit of the synthetic catalog project (a single module, `app.py`) identified one high-severity vulnerability: SQL injection in the legacy `search` function, which concatenates a user-controlled query-string argument directly into its SQL. The impact, demonstrated by executing the application's own functions locally with synthetic data, is the bypass of the documented `published=1` access-control filter (disclosing unpublished products) and arbitrary database read via a UNION attack that dumped the full schema from `sqlite_master`. The versioned alternative, `search_v2`, implements the same feature correctly using bound parameters and is not vulnerable; the defect is specific to the concatenating implementation. Remediation is trivial and a minimal fix (parameterized query, already exemplified in `search_v2`) is provided.

# Methodology

White-box code audit of the supplied local project, per the engagement rules: all functions were reviewed, including versioned alternatives; findings were demonstrated by invoking the application's functions in a local Python process with synthetic data only; no external hosts or AWS services were contacted; documented trust boundaries (the `published=1` filter and the HTTP-query-string origin of the `query` argument) were treated as part of the application contract. One function was found vulnerable, one was confirmed as the safe control, and the finding was validated with baseline, attack, and control inputs.

# Technical Analysis

**Vulnerability: SQL injection in `app.py` `search(db, query)`** (High, CVSS 3.1 vector `AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N`, score 7.5, CWE-89).

The function executes `"SELECT id,name FROM products WHERE published=1 AND name LIKE '%" + query + "%'"`. The `query` value — documented as originating from an HTTP query string — is concatenated into the SQL text with no validation, escaping, or allowlisting anywhere on the path to `db.execute`. A single quote terminates the string literal, after which arbitrary SQL runs:

- `"book' OR 1=1 --"` returned both rows, including `(2, 'unreleased book')`, defeating the `published=1` access-control filter (a documented trust boundary).
- `"x' UNION SELECT 1, sql FROM sqlite_master --"` returned the full schema, demonstrating arbitrary read of any table in the database.

The negative control isolates the root cause: the same payloads against `search_v2`, which binds the value as a parameter (`LIKE ?` with `('%' + query + '%',)`), return no rows. One report per distinct defect was filed; the parameterized variant required no report. No other functions or attack surfaces exist in this project.

# Recommendations

**Immediate**
1. Replace the concatenated query in `search` with the parameterized form already implemented in `search_v2`: `db.execute('SELECT id,name FROM products WHERE published=1 AND name LIKE ?', ('%' + query + '%',))` — bound parameters treat the user value as data, not SQL.

**Short-term**
2. If `search_v2` is the intended replacement, remove the legacy `search` function or gate it so no reachable code path constructs SQL by string concatenation; keeping both leaves the injectable version exposed.

**Retest and validation:** after the change, re-run the exact payloads from the proof — `"book' OR 1=1 --"` and `"x' UNION SELECT 1, sql FROM sqlite_master --"` — and confirm both return no rows while the normal `"book"` query still returns the published product.

