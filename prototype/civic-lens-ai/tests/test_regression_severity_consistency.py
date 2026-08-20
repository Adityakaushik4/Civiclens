import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.duplicates import master_issue_store
from app.schemas import MasterIssueModel
from app.duplicates.store import MasterIssueRecord
from app.taxonomy import Category
from datetime import datetime, timezone

client = TestClient(app)

def test_api_master_issues_severity_priority_consistency():
    """
    REGRESSION TEST:
    Proves that the backend API endpoint (GET /api/v1/ai/master-issues)
    always returns a `priority_level` that correctly matches the canonical
    mapping of the underlying `severity_score` (5=CRITICAL, 4=HIGH, 3=MEDIUM, 1-2=LOW).
    This ensures that the Issue Triage (which uses priority_level) and the
    Public Map (which uses severity_score) cannot disagree on the severity label.
    """
    
    # 1. Clear the store and insert test issues with different severities
    master_issue_store.clear()
    
    now_str = datetime.now(timezone.utc).isoformat()
    
    test_issues = [
        MasterIssueRecord(
            id="TEST-SEV-5",
            title="Critical Issue",
            category=Category.ROAD_DAMAGE,
            subcategory="POTHOLE",
            severity_score=5,
            latitude=20.0,
            longitude=85.0
        ),
        MasterIssueRecord(
            id="TEST-SEV-4",
            title="High Issue",
            category=Category.ROAD_DAMAGE,
            subcategory="POTHOLE",
            severity_score=4,
            latitude=20.0,
            longitude=85.0
        ),
        MasterIssueRecord(
            id="TEST-SEV-3",
            title="Medium Issue",
            category=Category.ROAD_DAMAGE,
            subcategory="POTHOLE",
            severity_score=3,
            latitude=20.0,
            longitude=85.0
        ),
        MasterIssueRecord(
            id="TEST-SEV-2",
            title="Low Issue 2",
            category=Category.ROAD_DAMAGE,
            subcategory="POTHOLE",
            severity_score=2,
            latitude=20.0,
            longitude=85.0
        ),
        MasterIssueRecord(
            id="TEST-SEV-1",
            title="Low Issue 1",
            category=Category.ROAD_DAMAGE,
            subcategory="POTHOLE",
            severity_score=1,
            latitude=20.0,
            longitude=85.0
        )
    ]
    
    for issue in test_issues:
        master_issue_store.add(issue)
        
    # 2. Fetch from the API
    response = client.get("/api/v1/ai/master-issues")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 5
    
    # 3. Assert canonical mapping for each returned issue
    for item in data:
        sev = item["severity_score"]
        pri = item["priority_level"]
        
        if sev == 5:
            assert pri == "CRITICAL", f"Expected CRITICAL for severity 5, got {pri}"
        elif sev == 4:
            assert pri == "HIGH", f"Expected HIGH for severity 4, got {pri}"
        elif sev == 3:
            assert pri == "MEDIUM", f"Expected MEDIUM for severity 3, got {pri}"
        elif sev <= 2:
            assert pri == "LOW", f"Expected LOW for severity <=2, got {pri}"
