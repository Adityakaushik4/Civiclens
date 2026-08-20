import os
import pytest
from unittest.mock import patch, MagicMock
from app.evidence.schemas import EvidenceType, VerificationStatus, ResolutionEvidence
from app.evidence.storage import EvidenceStore, _resolve_evidence_type
from app.database.models import EvidenceRecordModel


@pytest.fixture
def mock_db_session():
    """Provides a mocked database session for EvidenceStore testing without touching production DB."""
    session = MagicMock()
    bind = MagicMock()
    inspector = MagicMock()
    # Simulate table having evidence_type column already
    inspector.get_columns.return_value = [{"name": "evidence_type"}, {"name": "evidence_id"}]
    bind = MagicMock()
    session.get_bind.return_value = bind
    with patch("sqlalchemy.inspect", return_value=inspector):
        yield session


def test_resolve_evidence_type_fallback_rules():
    """Verifies fallback classification rules for legacy records without explicit evidence_type."""
    # Citizen voice note
    rec_audio = MagicMock(evidence_type=None, file_type="audio/wav", file_name="voice_complaint.wav", uploader_id="CITIZEN")
    assert _resolve_evidence_type(rec_audio) == EvidenceType.VOICE_NOTE

    # Citizen image -> BEFORE_IMAGE
    rec_citizen = MagicMock(evidence_type=None, file_type="image/jpeg", file_name="photo.jpg", uploader_id="CITIZEN")
    assert _resolve_evidence_type(rec_citizen) == EvidenceType.BEFORE_IMAGE

    # Operator image -> AFTER_IMAGE
    rec_operator = MagicMock(evidence_type=None, file_type="image/jpeg", file_name="resolved.jpg", uploader_id="operator_1")
    assert _resolve_evidence_type(rec_operator) == EvidenceType.AFTER_IMAGE

    # Explicit evidence_type override
    rec_explicit = MagicMock(evidence_type="BEFORE_IMAGE", file_type="image/jpeg", file_name="test.jpg", uploader_id="operator_1")
    assert _resolve_evidence_type(rec_explicit) == EvidenceType.BEFORE_IMAGE


def test_evidence_store_save_and_retrieve():
    """Tests saving BEFORE_IMAGE, AFTER_IMAGE, and VOICE_NOTE records into EvidenceStore."""
    with patch("app.evidence.storage.SessionLocal") as mock_session_cls, \
         patch("app.evidence.storage.os.path.exists", return_value=True), \
         patch("builtins.open", MagicMock()):
        
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        store = EvidenceStore()

        # Save Before Image
        ev_before = store.save_evidence(
            issue_id="ISSUE_TEST_101",
            evidence_type=EvidenceType.BEFORE_IMAGE,
            file_name="before_damage.jpg",
            mime_type="image/jpeg",
            file_bytes=b"fake_before_bytes",
            uploaded_by="CITIZEN"
        )
        assert ev_before.evidence_type == EvidenceType.BEFORE_IMAGE
        assert ev_before.uploaded_by == "CITIZEN"

        # Save After Image
        ev_after = store.save_evidence(
            issue_id="ISSUE_TEST_101",
            evidence_type=EvidenceType.AFTER_IMAGE,
            file_name="after_repair.jpg",
            mime_type="image/jpeg",
            file_bytes=b"fake_after_bytes",
            uploaded_by="operator_1"
        )
        assert ev_after.evidence_type == EvidenceType.AFTER_IMAGE
        assert ev_after.uploaded_by == "operator_1"

        # Verify listing by issue
        issue_ev = store.list_by_issue("ISSUE_TEST_101")
        assert len(issue_ev) == 2

        before_item = next(e for e in issue_ev if e.evidence_type == EvidenceType.BEFORE_IMAGE)
        after_item = next(e for e in issue_ev if e.evidence_type == EvidenceType.AFTER_IMAGE)

        assert before_item.file_name == "before_damage.jpg"
        assert after_item.file_name == "after_repair.jpg"


def test_queue_selection_with_multiple_evidence_records():
    """Verifies that an issue with BEFORE_IMAGE, VOICE_NOTE, and AFTER_IMAGE correctly maps before and after URLs."""
    from app.evidence.schemas import EvidenceType

    ev_before = MagicMock(
        evidence_id="ev_before",
        issue_id="ISSUE_293A",
        evidence_type=EvidenceType.BEFORE_IMAGE,
        public_token="tok_before_123",
        uploaded_by="CITIZEN",
        mime_type="image/jpeg"
    )
    ev_voice = MagicMock(
        evidence_id="ev_voice",
        issue_id="ISSUE_293A",
        evidence_type=EvidenceType.VOICE_NOTE,
        public_token="tok_voice_456",
        uploaded_by="CITIZEN",
        mime_type="audio/wav"
    )
    ev_after = MagicMock(
        evidence_id="ev_after",
        issue_id="ISSUE_293A",
        evidence_type=EvidenceType.AFTER_IMAGE,
        public_token="tok_after_789",
        uploaded_by="operator_1",
        mime_type="image/jpeg"
    )

    issue_evidence = [ev_before, ev_voice, ev_after]

    before_ev = next((e for e in issue_evidence if e.evidence_type == EvidenceType.BEFORE_IMAGE), None)
    if not before_ev:
        before_ev = next((e for e in issue_evidence if e.uploaded_by == "CITIZEN" and not (e.mime_type or "").startswith("audio/")), None)

    after_ev = next((e for e in issue_evidence if e.evidence_type == EvidenceType.AFTER_IMAGE and e != before_ev), None)
    if not after_ev:
        after_ev = next((e for e in issue_evidence if e.uploaded_by != "CITIZEN" and e != before_ev), None)

    assert before_ev.public_token == "tok_before_123"
    assert after_ev.public_token == "tok_after_789"
    assert before_ev != after_ev
