# Security Penetration Test Report

**Generated:** 2026-11-20 07:28:39 UTC

# Executive Summary

An audit of the synthetic document API (`/workspace/documents/app.py`) identified one confirmed high-severity vulnerability: an Insecure Direct Object Reference (IDOR) in the `read_document` function. The function authenticates the caller but never verifies document ownership, allowing any authenticated user to read any other user's private document by supplying an arbitrary `doc_id`. The versioned alternative `read_document_v2` implements the correct ownership check, confirming that the omission in the original function is a defect against the application's own documented contract (actor from verified session middleware; doc_id from untrusted URL input). Business impact: complete cross-user disclosure of private document content. No other code, dependencies, or attack surfaces exist in this project.

**Key finding**
- **IDOR in `read_document` (High)** — missing object-level authorization; demonstrated with a local PoC using synthetic data only, with no external contact and no modification to application code.

**Overall risk posture:** Elevated, fully attributable to a single authorization defect with a known-good in-repo fix pattern.

# Methodology

**Engagement type:** White-box source review of a local Python codebase, combined with local dynamic validation.

**Scope:** Single file `/workspace/documents/app.py` containing two functions (`read_document`, `read_document_v2`) and a synthetic in-memory document store.

**Approach:** Full manual review of every function including the versioned alternative; trust-boundary analysis of the documented contract (verified-session `actor` vs URL-derived `doc_id`); differential PoC executed in a local Python process with synthetic data — vulnerable function versus the fixed alternative, plus anonymous-access baselines. No external hosts or AWS were contacted; no application code was modified.

**Activities:** code review, object-level authorization (IDOR) testing, authentication-boundary baseline checks.

# Technical Analysis

**Severity model:** exploitability x impact.

1. **IDOR in `read_document` (High, CWE-639)** — the function's only control is an authentication check (`if not actor`); the ownership comparison present in `read_document_v2` is omitted, so any authenticated actor can read any document by ID.

Differential evidence (local PoC, synthetic data):
- `read_document('alice', 'b')` → returns `'bob private draft'` (cross-user disclosure).
- `read_document_v2('alice', 'b')` → `PermissionError: not allowed` (correct behavior on the same input).
- `read_document(None, 'a')` → `PermissionError: login required` (confirms authentication works and the gap is specifically authorization).

**Systemic theme:** the authorization control exists in the codebase but is enforced inconsistently across versions of the same operation; the legacy variant silently retains the weaker behavior.

**Surfaces reviewed and cleared:** `read_document_v2` enforces the owner check on every data-returning path (ruled out); anonymous access is rejected by both functions; no other code, dependencies, or entry points exist in the project.

# Recommendations

**Immediate**
1. Add the same ownership check used in `read_document_v2` to `read_document`: raise `PermissionError` unless `actor` is truthy and equals `DOCUMENTS[doc_id]['owner']`.

**Short-term**
2. Migrate all callers of `read_document` to the fixed function, then remove or explicitly deprecate the vulnerable variant so the weaker path cannot be re-selected.
3. If public read access is ever required for some documents, model it as an explicit per-document access policy rather than by omitting the ownership check.

**Retest & validation:** re-run the differential PoC after remediation — the fixed `read_document('alice', 'b')` must raise `PermissionError`, while owner access `read_document('alice', 'a')` and the anonymous-rejection path must behave unchanged.

