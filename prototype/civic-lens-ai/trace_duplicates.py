import sqlite3
import json

DB_PATH = "civic_lens.db"

def trace():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    report = {}

    cursor.execute("SELECT id, title, category, subcategory, citizen_reporter_count FROM master_issues WHERE citizen_reporter_count > 1")
    merged_issues = [dict(row) for row in cursor.fetchall()]
    report['merged_master_issues'] = merged_issues

    cursor.execute("SELECT * FROM duplicate_reviews")
    dup_reviews = [dict(row) for row in cursor.fetchall()]
    report['duplicate_reviews'] = dup_reviews

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    trace()
