import sqlite3
import json

DB_PATH = "civic_lens.db"

def audit():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    report = {}

    # Check master_issues for WATERLOGGING_ROAD
    cursor.execute("SELECT id, category, subcategory FROM master_issues WHERE subcategory = 'WATERLOGGING_ROAD'")
    report['old_waterlogging_master_issues'] = [dict(row) for row in cursor.fetchall()]

    # Check master_issues for WATERLOGGING
    cursor.execute("SELECT id, category, subcategory FROM master_issues WHERE subcategory = 'WATERLOGGING'")
    report['new_waterlogging_master_issues'] = [dict(row) for row in cursor.fetchall()]

    # Check routing_decisions for WATERLOGGING_ROAD
    cursor.execute("SELECT decision_id, issue_id, category, subcategory, primary_department FROM routing_decisions WHERE subcategory = 'WATERLOGGING_ROAD'")
    report['old_waterlogging_routing'] = [dict(row) for row in cursor.fetchall()]

    # Check routing_decisions for WATERLOGGING
    cursor.execute("SELECT decision_id, issue_id, category, subcategory, primary_department FROM routing_decisions WHERE subcategory = 'WATERLOGGING'")
    report['new_waterlogging_routing'] = [dict(row) for row in cursor.fetchall()]

    # Check duplicate_reviews for WATERLOGGING_ROAD
    cursor.execute("SELECT review_id, category, subcategory FROM duplicate_reviews WHERE subcategory = 'WATERLOGGING_ROAD'")
    report['old_waterlogging_duplicates'] = [dict(row) for row in cursor.fetchall()]

    # Check duplicate_reviews for WATERLOGGING
    cursor.execute("SELECT review_id, category, subcategory FROM duplicate_reviews WHERE subcategory = 'WATERLOGGING'")
    report['new_waterlogging_duplicates'] = [dict(row) for row in cursor.fetchall()]

    # Check non-waterlogging ROAD_DAMAGE
    cursor.execute("SELECT id, category, subcategory FROM master_issues WHERE category = 'ROAD_DAMAGE'")
    report['road_damage_master_issues'] = [dict(row) for row in cursor.fetchall()]

    # Print nicely
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    audit()
