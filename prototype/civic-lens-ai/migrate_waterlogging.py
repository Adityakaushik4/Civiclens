import sqlite3
import os

DB_PATH = "civic_lens.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} does not exist. Nothing to migrate.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Update master issues
        cursor.execute("""
            UPDATE master_issues 
            SET category = 'DRAINAGE', subcategory = 'WATERLOGGING' 
            WHERE subcategory = 'WATERLOGGING_ROAD'
        """)
        master_updated = cursor.rowcount

        # Update routing decisions
        cursor.execute("""
            UPDATE routing_decisions 
            SET category = 'DRAINAGE', subcategory = 'WATERLOGGING', primary_department = 'Drainage & Sewerage' 
            WHERE subcategory = 'WATERLOGGING_ROAD'
        """)
        routing_updated = cursor.rowcount

        # Update duplicate reviews
        cursor.execute("""
            UPDATE duplicate_reviews 
            SET category = 'DRAINAGE', subcategory = 'WATERLOGGING' 
            WHERE subcategory = 'WATERLOGGING_ROAD'
        """)
        duplicate_updated = cursor.rowcount
        
        # Check if issue_lifecycles has any category references? issue_lifecycles only has current_status and current_department
        # Need to update current_department if it was set to Roads & PWD for these issues
        cursor.execute("""
            UPDATE issue_lifecycles
            SET current_department = 'Drainage & Sewerage'
            WHERE issue_id IN (
                SELECT id FROM master_issues WHERE category = 'DRAINAGE' AND subcategory = 'WATERLOGGING'
            ) AND current_department = 'Roads & PWD'
        """)
        lifecycles_updated = cursor.rowcount

        conn.commit()
        print(f"Migration successful.")
        print(f"- Master issues updated: {master_updated}")
        print(f"- Routing decisions updated: {routing_updated}")
        print(f"- Duplicate reviews updated: {duplicate_updated}")
        print(f"- Issue lifecycles updated: {lifecycles_updated}")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
