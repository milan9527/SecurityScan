"""Disposable local authentication review fixture. No network or real data."""
import sqlite3


def database():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE users (name TEXT, password TEXT)")
    conn.execute("INSERT INTO users VALUES (?, ?)", ("demo", "fixture-password"))
    return conn


def login(name, password):
    with database() as conn:
        query = f"SELECT name FROM users WHERE name = '{name}' AND password = '{password}'"
        return conn.execute(query).fetchone() is not None


def login_parameterized(name, password):
    with database() as conn:
        return conn.execute(
            "SELECT name FROM users WHERE name = ? AND password = ?",
            (name, password),
        ).fetchone() is not None
