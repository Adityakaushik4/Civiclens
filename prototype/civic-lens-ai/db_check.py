import sqlite3
import sys

def main():
    conn = sqlite3.connect('civic_lens.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    counts = {}
    for t in tables:
        name = t[0]
        cursor.execute(f"SELECT count(*) FROM {name}")
        counts[name] = cursor.fetchone()[0]
        
    print("COUNTS:")
    for k, v in counts.items():
        print(f"{k}: {v}")
        
    print("\nMASTER_ISSUES:")
    cursor.execute("SELECT * FROM master_issues")
    for r in cursor.fetchall(): print(r)
    
    if 'issue_lifecycles' in counts:
        print("\nLIFECYCLES:")
        cursor.execute("SELECT * FROM issue_lifecycles")
        for r in cursor.fetchall(): print(r)
        
    print("\nROUTING:")
    cursor.execute("SELECT * FROM routing_decisions")
    for r in cursor.fetchall(): print(r)

if __name__ == '__main__':
    main()
