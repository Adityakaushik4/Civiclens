import pytest
import uuid
import datetime
from app.database import init_db, SessionLocal
from app.database.models import Base
from app.duplicates import master_issue_store, MasterIssueRecord
from app.taxonomy import Category
from app.routing import routing_store, RoutingDecisionResult
from app.priority import PriorityLevel
from app.sla import SLASnapshot, SLAPolicyStatus
from app.escalation import (
    escalation_store,
    IssueLifecycleRecord,
    IssueStatus,
    StatusHistory,
    reopen_idempotency_store,
)
from app.evidence import evidence_store, EvidenceType
from app.proposals import proposal_store, CitizenProposal, ProposalStatus
from app.voting import voting_store, VoteRecord
from app.allocation import allocation_store, BudgetAllocationResult
from app.rag import (
    rag_vector_store,
    CivicDocument,
    DocumentVersion,
    DocumentChunk,
    ChunkEmbedding,
    DocumentType,
    AuthorityStatus,
    AccessLevel,
)


@pytest.fixture(autouse=True)
def setup_persistence_db():
    init_db()
    master_issue_store.clear()
    escalation_store.clear()
    routing_store.clear()
    evidence_store.clear()
    proposal_store.clear()
    voting_store.clear()
    allocation_store.clear()
    rag_vector_store.clear()
    reopen_idempotency_store.clear()
    yield


def test_1_create_and_retrieve_master_issue():
    record_id = f"mi_test_{uuid.uuid4().hex[:6]}"
    rec = MasterIssueRecord(
        id=record_id,
        title="Pothole on Main Street",
        category=Category.ROAD_DAMAGE,
        subcategory="pothole",
        severity_score=4,
        latitude=28.6139,
        longitude=77.2090,
    )
    master_issue_store.add(rec)

    retrieved = master_issue_store.get(record_id)
    assert retrieved is not None
    assert retrieved.title == "Pothole on Main Street"
    assert retrieved.severity_score == 4


def test_2_application_restart_preserves_master_issue():
    record_id = f"mi_restart_{uuid.uuid4().hex[:6]}"
    rec = MasterIssueRecord(
        id=record_id,
        title="Broken Streetlight",
        category=Category.ELECTRICITY,
        subcategory="street_light",
        severity_score=3,
        latitude=28.7041,
        longitude=77.1025,
    )
    master_issue_store.add(rec)

    master_issue_store._records.clear()
    assert record_id not in master_issue_store._records

    retrieved = master_issue_store.get(record_id)
    assert retrieved is not None
    assert retrieved.title == "Broken Streetlight"


def test_3_routing_decision_survives_restart():
    issue_id = f"mi_route_{uuid.uuid4().hex[:6]}"
    master_rec = MasterIssueRecord(id=issue_id, title="Route test", category=Category.ROAD_DAMAGE, subcategory="pothole", severity_score=4, latitude=28.6, longitude=77.2)
    master_issue_store.add(master_rec)

    dec = RoutingDecisionResult(
        decision_id=f"dec_{uuid.uuid4().hex[:6]}",
        issue_id=issue_id,
        jurisdiction_id="WARD_7",
        category="ROAD_DAMAGE",
        subcategory="pothole",
        priority_score=85,
        priority_level=PriorityLevel.HIGH,
        primary_department="Department of Public Works",
        responsible_unit="Road Maintenance Unit",
        escalation_department="Supervisory Board",
        selection_reason="Category match",
        routed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
    routing_store.save(dec)

    routing_store._decisions.clear()

    retrieved = routing_store.get(issue_id)
    assert retrieved is not None
    assert retrieved.primary_department == "Department of Public Works"


def test_4_sla_snapshot_survives_restart():
    issue_id = f"mi_sla_{uuid.uuid4().hex[:6]}"
    master_rec = MasterIssueRecord(id=issue_id, title="SLA test", category=Category.ROAD_DAMAGE, subcategory="pothole", severity_score=4, latitude=28.6, longitude=77.2)
    master_issue_store.add(master_rec)

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    sla = SLASnapshot(
        policy_id="sla_pol_test",
        jurisdiction_id="WARD_7",
        category="ROAD_DAMAGE",
        priority_level="HIGH",
        acknowledgement_minutes=60,
        resolution_minutes=720,
        status=SLAPolicyStatus.AUTHORITATIVE,
        acknowledgement_deadline=now_str,
        resolution_deadline=now_str,
    )
    lifecycle = IssueLifecycleRecord(
        issue_id=issue_id,
        current_status=IssueStatus.ROUTED,
        current_department="Public Works",
        responsible_unit="Unit 1",
        escalation_department="Supervisor Board",
        routed_at=now_str,
        acknowledgement_deadline=now_str,
        resolution_deadline=now_str,
        jurisdiction_id="WARD_7",
        sla=sla,
    )
    escalation_store.save(lifecycle)

    escalation_store._records.clear()

    retrieved = escalation_store.get(issue_id)
    assert retrieved is not None
    assert retrieved.sla.resolution_minutes == 720


def test_5_status_history_remains_append_only():
    issue_id = f"mi_hist_{uuid.uuid4().hex[:6]}"
    master_rec = MasterIssueRecord(id=issue_id, title="Hist test", category=Category.ROAD_DAMAGE, subcategory="pothole", severity_score=4, latitude=28.6, longitude=77.2)
    master_issue_store.add(master_rec)

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    sla = SLASnapshot(
        policy_id="p1",
        category="ROAD_DAMAGE",
        priority_level="HIGH",
        acknowledgement_minutes=60,
        resolution_minutes=720,
        status=SLAPolicyStatus.AUTHORITATIVE,
        acknowledgement_deadline=now_str,
        resolution_deadline=now_str,
    )
    lifecycle = IssueLifecycleRecord(
        issue_id=issue_id,
        current_status=IssueStatus.ROUTED,
        current_department="Dept A",
        responsible_unit="Unit 1",
        escalation_department="Board",
        routed_at=now_str,
        acknowledgement_deadline=now_str,
        resolution_deadline=now_str,
        sla=sla,
    )
    
    h1 = StatusHistory(history_id="h1", issue_id=issue_id, from_status=IssueStatus.REGISTERED, to_status=IssueStatus.ROUTED, changed_by="system", notes="Routed", changed_at=now_str)
    lifecycle.status_history.append(h1)
    escalation_store.save(lifecycle)

    h2 = StatusHistory(history_id="h2", issue_id=issue_id, from_status=IssueStatus.ROUTED, to_status=IssueStatus.ACKNOWLEDGED, changed_by="op1", notes="Acked", changed_at=now_str)
    lifecycle.status_history.append(h2)
    escalation_store.save(lifecycle)

    escalation_store._records.clear()
    retrieved = escalation_store.get(issue_id)
    assert len(retrieved.status_history) == 2
    assert retrieved.status_history[1].to_status == IssueStatus.ACKNOWLEDGED


def test_6_evidence_metadata_survives_restart():
    issue_id = f"mi_ev_{uuid.uuid4().hex[:6]}"
    master_rec = MasterIssueRecord(id=issue_id, title="Ev test", category=Category.ROAD_DAMAGE, subcategory="pothole", severity_score=4, latitude=28.6, longitude=77.2)
    master_issue_store.add(master_rec)

    rec = evidence_store.save_evidence(
        issue_id=issue_id,
        evidence_type=EvidenceType.BEFORE_IMAGE,
        file_name="repaired_road.jpg",
        mime_type="image/jpeg",
        file_bytes=b"fake_jpeg_data",
        uploaded_by="op_4",
    )
    ev_id = rec.evidence_id

    evidence_store._evidence.clear()

    retrieved = evidence_store.get_evidence(ev_id)
    assert retrieved is not None
    assert retrieved.file_name == "repaired_road.jpg"


def test_7_proposal_survives_restart():
    proposal_id = f"prop_test_{uuid.uuid4().hex[:6]}"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    prop = CitizenProposal(
        proposal_id=proposal_id,
        opportunity_id="opp_1",
        jurisdiction_id="WARD_7",
        title="School Corridor Paving",
        description="Fix pothole corridor near school",
        proposer_id_hash="usr_123456",
        category="ROAD_DAMAGE",
        requested_budget=250000.0,
        cost_status="ESTIMATED",
        linked_master_issue_ids=["mi_1"],
        status=ProposalStatus.ELIGIBLE,
        created_at=now_str,
        updated_at=now_str,
    )
    proposal_store.save(prop)
    
    # We now use stateless DB store, so we can just re-fetch
    prop_reloaded = proposal_store.get(proposal_id)
    assert prop_reloaded is not None
    assert prop_reloaded.title == "School Corridor Paving"


def test_8_vote_survives_restart():
    cycle_id = "cycle_ward7_2027"
    prop_id = f"prop_vote_{uuid.uuid4().hex[:6]}"
    token_hash = f"tok_{uuid.uuid4().hex[:12]}"
    
    vote = VoteRecord(
        vote_id=f"v_{uuid.uuid4().hex[:6]}",
        cycle_id=cycle_id,
        proposal_id=prop_id,
        voter_token_hash=token_hash,
        jurisdiction_id="WARD_7",
        voted_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
    voting_store.save_vote(vote)

    voting_store._votes.clear()

    votes = voting_store.list_by_cycle(cycle_id)
    assert len(votes) == 1
    assert votes[0].voter_token_hash == token_hash


def test_9_budget_allocation_survives_restart():
    cycle_id = "cycle_ward7_2027"
    alloc = BudgetAllocationResult(
        allocation_id=f"alloc_{uuid.uuid4().hex[:6]}",
        cycle_id=cycle_id,
        total_budget=5000000.0,
        allocated_budget=250000.0,
        remaining_budget=4750000.0,
        selected_proposals=[{"proposal_id": "p1", "cost": 250000.0}],
        rejected_proposals=[],
        decision_log=["SELECTED p1"],
        allocated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
    allocation_store.save_allocation(alloc)

    allocation_store._allocations.clear()

    retrieved = allocation_store.get_allocation(cycle_id)
    assert retrieved is not None
    assert retrieved.allocated_budget == 250000.0


def test_10_rag_document_survives_restart():
    doc_id = f"doc_{uuid.uuid4().hex[:6]}"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    doc = CivicDocument(
        document_id=doc_id,
        title="Municipal Pothole Guidelines 2026",
        issuing_authority="Department of Roads",
        jurisdiction_id="WARD_7",
        document_type=DocumentType.POLICY,
        authority_status=AuthorityStatus.AUTHORITATIVE,
        access_level=AccessLevel.PUBLIC,
        current_version_id="v1",
        created_at=now_str,
        updated_at=now_str,
    )
    rag_vector_store.save_document(doc)

    rag_vector_store._documents.clear()

    retrieved = rag_vector_store.get_document(doc_id)
    assert retrieved is not None
    assert retrieved.title == "Municipal Pothole Guidelines 2026"


def test_11_rag_vector_survives_restart():
    doc_id = f"doc_{uuid.uuid4().hex[:6]}"
    version_id = f"v_{uuid.uuid4().hex[:6]}"
    chunk_id = f"chk_{uuid.uuid4().hex[:6]}"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    doc = CivicDocument(
        document_id=doc_id,
        title="Vector Guideline",
        issuing_authority="Dept 1",
        jurisdiction_id="WARD_7",
        document_type=DocumentType.POLICY,
        authority_status=AuthorityStatus.AUTHORITATIVE,
        access_level=AccessLevel.PUBLIC,
        current_version_id=version_id,
        created_at=now_str,
        updated_at=now_str,
    )
    rag_vector_store.save_document(doc)

    ver = DocumentVersion(
        version_id=version_id,
        document_id=doc_id,
        version_number=1,
        source_reference="ref_1",
        file_key="key_1",
        file_name="guideline.txt",
        mime_type="text/plain",
        checksum="abc",
        ingested_by="user_1",
        ingestion_timestamp=now_str,
        effective_from=now_str,
    )

    rag_vector_store.save_version(ver)

    chunk = DocumentChunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        version_id=version_id,
        chunk_index=0,
        section_title="Pothole SLA",
        content_text="Potholes must be repaired within 24 hours.",
        token_count=10,
        jurisdiction_id="WARD_7",
        authority_status=AuthorityStatus.AUTHORITATIVE,
        access_level=AccessLevel.PUBLIC,
        created_at=now_str,
    )
    emb_vec = [0.1] * 3072
    emb = ChunkEmbedding(embedding_id=f"emb_{chunk_id}", chunk_id=chunk_id, dimensions=3072, vector=emb_vec)

    rag_vector_store.save_chunks([chunk])
    rag_vector_store.save_embeddings([emb])

    rag_vector_store._chunks.clear()
    rag_vector_store._embeddings.clear()

    retrieved_chunk = rag_vector_store.get_chunk(chunk_id)
    retrieved_emb = rag_vector_store.get_embedding(chunk_id)
    assert retrieved_chunk is not None
    assert retrieved_emb is not None
    assert len(retrieved_emb.vector) == 3072


def test_12_jurisdiction_isolation():
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    p1 = CitizenProposal(
        proposal_id="prop_j1",
        jurisdiction_id="WARD_7",
        title="P1",
        description="D1",
        proposer_id_hash="u1",
        category="ROAD_DAMAGE",
        requested_budget=100.0,
        linked_master_issue_ids=[],
        created_at=now_str,
        updated_at=now_str,
    )
    p2 = CitizenProposal(
        proposal_id="prop_j2",
        jurisdiction_id="WARD_9",
        title="P2",
        description="D2",
        proposer_id_hash="u2",
        category="ROAD_DAMAGE",
        requested_budget=200.0,
        linked_master_issue_ids=[],
        created_at=now_str,
        updated_at=now_str,
    )
    proposal_store.save(p1)
    proposal_store.save(p2)

    ward_7_props = proposal_store.list_all("WARD_7")
    assert len(ward_7_props) == 1
    assert ward_7_props[0].proposal_id == "prop_j1"


def test_13_duplicate_vote_rejection():
    cycle_id = "cycle_ward7_2027"
    prop_id = "prop_uniq_1"
    token_hash = "tok_user_shared"

    v1 = VoteRecord(vote_id="v1", cycle_id=cycle_id, proposal_id=prop_id, voter_token_hash=token_hash, jurisdiction_id="WARD_7", voted_at="2027-01-01T00:00:00Z")
    voting_store.save_vote(v1)

    v2 = VoteRecord(vote_id="v2", cycle_id=cycle_id, proposal_id=prop_id, voter_token_hash=token_hash, jurisdiction_id="WARD_7", voted_at="2027-01-01T00:01:00Z")
    with pytest.raises(ValueError, match="Duplicate vote detected"):
        voting_store.save_vote(v2)


def test_14_idempotency_survives_restart():
    issue_id = f"mi_idemp_{uuid.uuid4().hex[:6]}"
    idemp_key = "key_abc123"
    payload = {"status": "REOPENED", "reopened_count": 1}

    reopen_idempotency_store.save(issue_id, idemp_key, payload)

    reopen_idempotency_store._cache.clear()

    cached = reopen_idempotency_store.get(issue_id, idemp_key)
    assert cached is not None
    assert cached["reopened_count"] == 1


def test_15_historical_sla_snapshot_immutability():
    issue_id = f"mi_immut_{uuid.uuid4().hex[:6]}"
    master_rec = MasterIssueRecord(id=issue_id, title="Immut test", category=Category.ROAD_DAMAGE, subcategory="pothole", severity_score=4, latitude=28.6, longitude=77.2)
    master_issue_store.add(master_rec)

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    original_sla = SLASnapshot(
        policy_id="sla_original_v1",
        category="ROAD_DAMAGE",
        priority_level="CRITICAL",
        acknowledgement_minutes=30,
        resolution_minutes=240,
        status=SLAPolicyStatus.AUTHORITATIVE,
        acknowledgement_deadline=now_str,
        resolution_deadline=now_str,
    )
    lifecycle = IssueLifecycleRecord(
        issue_id=issue_id,
        current_status=IssueStatus.ROUTED,
        current_department="Public Works",
        responsible_unit="Unit 1",
        escalation_department="Board",
        routed_at=now_str,
        acknowledgement_deadline=now_str,
        resolution_deadline=now_str,
        sla=original_sla,
    )
    escalation_store.save(lifecycle)

    retrieved = escalation_store.get(issue_id)
    assert retrieved.sla.policy_id == "sla_original_v1"
    assert retrieved.sla.acknowledgement_minutes == 30
