import sqlite3

def clean_db():
    conn = sqlite3.connect('civic_lens.db')
    cursor = conn.cursor()
    
    # 1. Fetch current records
    cursor.execute("SELECT id, title, category, citizen_reporter_count FROM master_issues")
    records = cursor.fetchall()
    
    print("CURRENT RECORDS IN DATABASE:")
    print("-" * 50)
    for r in records:
        print(f"ID: {r[0]}, Title: '{r[1]}', Category: {r[2]}, CitizenCount: {r[3]}")
        
    # 2. Classify and Delete
    deleted_ids = []
    for r in records:
        record_id = r[0]
        # All currently known IDs are from the residual test fixtures
        if record_id.startswith('mi_') or 'test' in record_id.lower() or 'test' in r[1].lower():
            cursor.execute("DELETE FROM master_issues WHERE id = ?", (record_id,))
            # Also clean up related records
            cursor.execute("DELETE FROM issue_lifecycles WHERE issue_id = ?", (record_id,))
            cursor.execute("DELETE FROM routing_decisions WHERE issue_id = ?", (record_id,))
            deleted_ids.append(record_id)
            
    conn.commit()
    conn.close()
    
    print("\nDELETED RECORDS:")
    print("-" * 50)
    for did in deleted_ids:
        print(f"Deleted test fixture: {did}")

if __name__ == "__main__":
    clean_db()
