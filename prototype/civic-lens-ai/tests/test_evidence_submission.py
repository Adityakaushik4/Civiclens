import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.evidence.schemas import EvidenceType
from app.evidence import evidence_store
import io

client = TestClient(app)

def test_citizen_report_missing_photo_rejected():
    """Verify that submitting a citizen report without a photo is rejected by the backend."""
    response = client.post(
        "/api/v1/issues/citizen-report",
        data={
            "category": "ROADS",
            "subcategory": "POTHOLE",
            "priority_score": 60,
            "priority_level": "MEDIUM",
        }
    )
    # FastAPI's built-in validation for missing File(...) is 422 Unprocessable Entity
    assert response.status_code == 422


def test_citizen_report_with_photo_success():
    """Verify that submitting with a photo correctly routes and saves BEFORE_IMAGE."""
    photo_bytes = b"fake_image_bytes"
    response = client.post(
        "/api/v1/issues/citizen-report",
        data={
            "category": "ROADS",
            "subcategory": "POTHOLE",
            "priority_score": 60,
            "priority_level": "MEDIUM",
            "latitude": 20.296,
            "longitude": 85.824,
        },
        files={
            "photo": ("test_pothole.jpg", io.BytesIO(photo_bytes), "image/jpeg")
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "issue_id" in data
    issue_id = data["issue_id"]
    
    # Verify BEFORE_IMAGE was persisted to EvidenceStore
    evidences = evidence_store.list_by_issue(issue_id)
    assert len(evidences) == 1
    assert evidences[0].evidence_type == EvidenceType.BEFORE_IMAGE
    assert evidences[0].file_name == "test_pothole.jpg"
    assert evidences[0].uploaded_by == "CITIZEN"


def test_citizen_report_with_photo_and_voice():
    """Verify that submitting with both photo and voice audio saves both evidence types."""
    photo_bytes = b"fake_image_bytes"
    audio_bytes = b"fake_audio_bytes"
    
    response = client.post(
        "/api/v1/issues/citizen-report",
        data={
            "category": "WATER",
            "subcategory": "LEAK",
            "priority_score": 80,
            "priority_level": "HIGH",
        },
        files={
            "photo": ("water_leak.jpg", io.BytesIO(photo_bytes), "image/jpeg"),
            "audio": ("voice_note.wav", io.BytesIO(audio_bytes), "audio/wav")
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    issue_id = data["issue_id"]
    
    # Verify both BEFORE_IMAGE and VOICE_NOTE were persisted
    evidences = evidence_store.list_by_issue(issue_id)
    assert len(evidences) == 2
    types = [e.evidence_type for e in evidences]
    assert EvidenceType.BEFORE_IMAGE in types
    assert EvidenceType.VOICE_NOTE in types
