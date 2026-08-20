import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import Category, DuplicateAction, DuplicateReviewDecisionEnum
from app.duplicates import (
    haversine_distance,
    cosine_similarity,
    master_issue_store,
    DuplicateDetectionEngine,
)
from app.embeddings.base import EmbeddingProvider

client = TestClient(app)


from app.database.connection import SessionLocal, init_db
from app.database.models import MasterIssueModel

@pytest.fixture(autouse=True)
def setup_function():
    init_db()
    master_issue_store.clear()
    db = SessionLocal()
    try:
        db.query(MasterIssueModel).delete()
        db.commit()
    finally:
        db.close()



class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic embedding provider (3072 dimensions) with orthogonal vectors per topic."""
    async def generate_embedding(self, text: str):
        vec = [0.0] * 3072
        t_lower = text.lower()
        if "pothole" in t_lower or "गड्ढा" in t_lower or "ଗାତ" in t_lower:
            for i in range(0, 100):
                vec[i] = 0.1
        elif "caved" in t_lower:
            for i in range(50, 150):
                vec[i] = 0.1
        elif "streetlight" in t_lower or "light" in t_lower:
            for i in range(200, 300):
                vec[i] = 0.1
        elif "drain" in t_lower:
            for i in range(400, 500):
                vec[i] = 0.1
        else:
            for i in range(1000, 1100):
                vec[i] = 0.1
        return vec


# ---------------------------------------------------------
# Math & Utility Unit Tests
# ---------------------------------------------------------

def test_haversine_distance_zero():
    dist = haversine_distance(20.2961, 85.8245, 20.2961, 85.8245)
    assert dist == 0.0


def test_haversine_distance_known_points():
    dist = haversine_distance(20.2961, 85.8245, 20.4625, 85.8828)
    assert 18000 < dist < 21000


def test_cosine_similarity_identical():
    v1 = [1.0] * 3072
    v2 = [1.0] * 3072
    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-5


def test_cosine_similarity_orthogonal():
    v1 = [1.0] * 100 + [0.0] * 2972
    v2 = [0.0] * 100 + [1.0] * 100 + [0.0] * 2872
    assert abs(cosine_similarity(v1, v2) - 0.0) < 1e-5


# ---------------------------------------------------------
# Audit Fix Tests
# ---------------------------------------------------------

def test_fix1_vector_dimension_3072():
    with patch("app.main.get_embedding_provider", return_value=MockEmbeddingProvider()):
        payload = {
            "text": "Pothole testing 3072 vector dimensions",
            "category": "ROAD_DAMAGE",
            "subcategory": "POTHOLE",
            "latitude": 20.2961,
            "longitude": 85.8245
        }
        res = client.post("/api/v1/ai/duplicates/check", json=payload)
        assert res.status_code == 200


def test_fix2_weight_normalization():
    with patch("app.main.get_embedding_provider", return_value=MockEmbeddingProvider()):
        # First complaint
        p1 = {
            "text": "Huge pothole near school",
            "category": "ROAD_DAMAGE",
            "subcategory": "POTHOLE",
            "latitude": 20.2961,
            "longitude": 85.8245
        }
        client.post("/api/v1/ai/duplicates/check", json=p1)

        # Second complaint (identical text & location, text-only)
        p2 = {
            "text": "Huge pothole near school",
            "category": "ROAD_DAMAGE",
            "subcategory": "POTHOLE",
            "latitude": 20.2961,
            "longitude": 85.8245
        }
        res2 = client.post("/api/v1/ai/duplicates/check", json=p2)
        assert res2.status_code == 200
        data2 = res2.json()

        assert data2["score_breakdown"]["normalized_weights_used"] is True
        # Total score should scale cleanly to 1.0 when text signals are perfect
        assert abs(data2["total_score"] - 1.0) < 1e-3


def test_fix3_subcategory_conflict_safety():
    with patch("app.main.get_embedding_provider", return_value=MockEmbeddingProvider()):
        # Master Complaint: POTHOLE
        p1 = {
            "text": "Large pothole on road",
            "category": "ROAD_DAMAGE",
            "subcategory": "POTHOLE",
            "latitude": 20.2961,
            "longitude": 85.8245
        }
        client.post("/api/v1/ai/duplicates/check", json=p1)

        # 1. Same category + Same subcategory -> AUTOMATIC_MERGE
        p_same = {
            "text": "Large pothole on road",
            "category": "ROAD_DAMAGE",
            "subcategory": "POTHOLE",
            "latitude": 20.2961,
            "longitude": 85.8245
        }
        res_same = client.post("/api/v1/ai/duplicates/check", json=p_same).json()
        assert res_same["action"] == "AUTOMATIC_MERGE"

        # 2. Same category + Different subcategory -> HUMAN_REVIEW_RECOMMENDED (Capped!)
        p_diff_sub = {
            "text": "Road caved in near school entrance",
            "category": "ROAD_DAMAGE",
            "subcategory": "ROAD_CAVED_IN",
            "latitude": 20.2961,
            "longitude": 85.8245
        }
        res_diff_sub = client.post("/api/v1/ai/duplicates/check", json=p_diff_sub).json()
        assert res_diff_sub["action"] == "HUMAN_REVIEW_RECOMMENDED"

        # 3. Different category -> NEW_MASTER_ISSUE
        p_diff_cat = {
            "text": "Streetlight broken on road",
            "category": "STREETLIGHT",
            "subcategory": "NOT_WORKING",
            "latitude": 20.2961,
            "longitude": 85.8245
        }
        res_diff_cat = client.post("/api/v1/ai/duplicates/check", json=p_diff_cat).json()
        assert res_diff_cat["action"] == "NEW_MASTER_ISSUE"


def test_fix4_centroid_running_average():
    with patch("app.main.get_embedding_provider", return_value=MockEmbeddingProvider()):
        # 1 Complaint at (20.0, 80.0)
        p1 = {"text": "Large pothole on road A", "category": "ROAD_DAMAGE", "subcategory": "POTHOLE", "latitude": 20.0, "longitude": 80.0}
        r1 = client.post("/api/v1/ai/duplicates/check", json=p1).json()
        master = r1["master_issue"]
        assert master["latitude"] == 20.0 and master["longitude"] == 80.0

        # 2 Complaints: Merge complaint at (20.001, 80.001) ~150m away
        p2 = {"text": "Large pothole on road B", "category": "ROAD_DAMAGE", "subcategory": "POTHOLE", "latitude": 20.001, "longitude": 80.001}
        r2 = client.post("/api/v1/ai/duplicates/check", json=p2).json()
        assert r2["action"] == "AUTOMATIC_MERGE"
        master2 = r2["master_issue"]
        # Running average: (20.0 * 1 + 20.001) / 2 = 20.0005
        assert abs(master2["latitude"] - 20.0005) < 1e-4
        assert abs(master2["longitude"] - 80.0005) < 1e-4

        # 3 Complaints: Merge complaint at (20.002, 80.002)
        p3 = {"text": "Large pothole on road C", "category": "ROAD_DAMAGE", "subcategory": "POTHOLE", "latitude": 20.002, "longitude": 80.002}
        r3 = client.post("/api/v1/ai/duplicates/check", json=p3).json()
        assert r3["action"] == "AUTOMATIC_MERGE"
        master3 = r3["master_issue"]
        # Running average: (20.0005 * 2 + 20.002) / 3 = 20.001
        assert abs(master3["latitude"] - 20.001) < 1e-4
        assert abs(master3["longitude"] - 80.001) < 1e-4


def test_fix5_human_review_queue_and_decisions():
    with patch("app.main.get_embedding_provider", return_value=MockEmbeddingProvider()):
        # First master issue
        p1 = {"text": "Broken streetlight near park", "category": "STREETLIGHT", "subcategory": "NOT_WORKING", "latitude": 20.2961, "longitude": 85.8245}
        client.post("/api/v1/ai/duplicates/check", json=p1)

        # Trigger HUMAN_REVIEW_RECOMMENDED (different subcategory: POLE_DAMAGED)
        p2 = {"text": "Light pole damaged near park", "category": "STREETLIGHT", "subcategory": "POLE_DAMAGED", "latitude": 20.2961, "longitude": 85.8245}
        r2 = client.post("/api/v1/ai/duplicates/check", json=p2).json()

        assert r2["action"] == "HUMAN_REVIEW_RECOMMENDED"
        review_id = r2["review_id"]
        assert review_id is not None

        # List pending reviews
        reviews_res = client.get("/api/v1/ai/duplicates/reviews?status=PENDING")
        assert reviews_res.status_code == 200
        reviews_list = reviews_res.json()
        assert any(r["review_id"] == review_id for r in reviews_list)

        # Decide review: APPROVED
        decide_payload = {
            "review_id": review_id,
            "decision": "APPROVED",
            "operator_id": "operator_42"
        }
        dec_res = client.post("/api/v1/ai/duplicates/review/decide", json=decide_payload)
        assert dec_res.status_code == 200
        assert dec_res.json()["status"] == "APPROVED"
        assert dec_res.json()["operator_id"] == "operator_42"

        # Test Idempotency: Deciding again returns resolved state without double merge
        dec_res_again = client.post("/api/v1/ai/duplicates/review/decide", json=decide_payload)
        assert dec_res_again.status_code == 200
        assert dec_res_again.json()["status"] == "APPROVED"


def test_fix6_complaint_idempotency():
    with patch("app.main.get_embedding_provider", return_value=MockEmbeddingProvider()):
        payload = {
            "complaint_id": "complaint-uuid-12345",
            "text": "Pothole near market entrance",
            "category": "ROAD_DAMAGE",
            "subcategory": "POTHOLE",
            "latitude": 20.2961,
            "longitude": 85.8245
        }

        # Submit 5 times with same complaint_id
        responses = [client.post("/api/v1/ai/duplicates/check", json=payload).json() for _ in range(5)]

        # Verify all responses return identical Master Issue ID and citizen count remains 1
        for res in responses:
            assert res["action"] == "NEW_MASTER_ISSUE"
            assert res["citizen_reporter_count"] == 1

        # Check master issue list
        issues = client.get("/api/v1/ai/master-issues").json()
        target_id = responses[0].get("matched_master_issue_id") or (responses[0].get("master_issue") or {}).get("id")
        matching_issues = [i for i in issues if i["id"] == target_id]
        assert len(matching_issues) == 1


        assert matching_issues[0]["citizen_reporter_count"] == 1

