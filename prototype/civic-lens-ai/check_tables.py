import sqlite3
import json

DB_PATH = "civic_lens.db"

def list_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print("Tables:", tables)

    for t in tables:
        if "public" in t or "anonymized" in t:
            print(f"--- Table {t} ---")
            conn.row_factory = sqlite3.Row
            c2 = conn.cursor()
            c2.execute(f"SELECT * FROM {t}")
            rows = [dict(r) for r in c2.fetchall()]
            print(json.dumps(rows, indent=2))
            
if __name__ == "__main__":
    list_tables()
