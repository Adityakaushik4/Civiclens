import sqlite3
import json
import os

DB_PATH = "civic_lens.db"

def dump_records():
    if not os.path.exists(DB_PATH):
        print(json.dumps({"error": f"Database not found at {DB_PATH}"}))
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    report = {}

    # 1. master_issues
    cursor.execute("SELECT id, title, category, subcategory, citizen_reporter_count FROM master_issues")
    report["master_issues"] = [dict(row) for row in cursor.fetchall()]

    # 2. routing_decisions
    cursor.execute("SELECT * FROM routing_decisions")
    report["routing_decisions"] = [dict(row) for row in cursor.fetchall()]

    # 3. issue_lifecycles
    cursor.execute("SELECT * FROM issue_lifecycles")
    report["issue_lifecycles"] = [dict(row) for row in cursor.fetchall()]

    # 4. Search for "waterlogging" in any table
    waterlogging_results = []
    # master_issues
    cursor.execute("SELECT id, title, category FROM master_issues WHERE title LIKE '%water%' OR title LIKE '%Chandrasekharpur%' OR category LIKE '%WATER%' OR subcategory LIKE '%WATER%'")
    waterlogging_results.extend([dict(row) for row in cursor.fetchall()])
    # citizen_reports (assuming table is called complaints or citizen_reports)
    # Let's check table names first
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row['name'] for row in cursor.fetchall()]
    report["tables"] = tables
    if 'complaints' in tables:
        cursor.execute("SELECT id, complaint_text FROM complaints WHERE complaint_text LIKE '%water%' OR complaint_text LIKE '%Chandrasekharpur%'")
        waterlogging_results.extend([dict(row) for row in cursor.fetchall()])
    
    report["waterlogging_search_results"] = waterlogging_results

    # Print the report
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    dump_records()
