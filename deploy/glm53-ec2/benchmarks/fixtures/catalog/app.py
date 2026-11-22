"""Synthetic catalog search; the query argument comes from an HTTP query string."""
import sqlite3

def database():
    db = sqlite3.connect(':memory:')
    db.executescript("CREATE TABLE products(id INTEGER, name TEXT, published INTEGER); INSERT INTO products VALUES(1,'public book',1),(2,'unreleased book',0);")
    return db

def search(db, query):
    return db.execute("SELECT id,name FROM products WHERE published=1 AND name LIKE '%" + query + "%'").fetchall()

def search_v2(db, query):
    return db.execute('SELECT id,name FROM products WHERE published=1 AND name LIKE ?', ('%' + query + '%',)).fetchall()
