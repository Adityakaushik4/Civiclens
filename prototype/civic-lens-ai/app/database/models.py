import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    JSON,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from app.database.connection import Base


# =====================================================================
# A & B. Master Issues & Complaints
# =====================================================================
class MasterIssueModel(Base):
    __tablename__ = "master_issues"

    id = Column(String(64), primary_key=True)
    title = Column(String(256), nullable=False)
    category = Column(String(64), nullable=False, index=True)
    subcategory = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="OPEN", index=True)
    severity_score = Column(Integer, nullable=False, default=1)
    citizen_reporter_count = Column(Integer, nullable=False, default=1)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address_description = Column(String(256), nullable=True)
    description = Column(String, nullable=True)
    embedding_json = Column(JSON, nullable=True)
    reporter_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc), index=True)

    __table_args__ = (
        Index("idx_master_issues_coords", "latitude", "longitude"),
    )


# =====================================================================
# C. Duplicate Reviews
# =====================================================================
class DuplicateReviewModel(Base):
    __tablename__ = "duplicate_reviews"

    review_id = Column(String(64), primary_key=True)
    complaint_id = Column(String(64), nullable=False, index=True)
    candidate_master_issue_id = Column(String(64), ForeignKey("master_issues.id"), nullable=False)
    similarity_score = Column(Float, nullable=False)
    score_breakdown_json = Column(JSON, nullable=False)
    complaint_lat = Column(Float, nullable=False)
    complaint_lon = Column(Float, nullable=False)
    complaint_text = Column(Text, nullable=False)
    category = Column(String(64), nullable=False)
    subcategory = Column(String(64), nullable=False)
    embedding_json = Column(JSON, nullable=True)
    status = Column(String(32), nullable=False, default="PENDING", index=True)
    operator_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)


# =====================================================================
# D. Routing Decisions
# =====================================================================
class RoutingDecisionModel(Base):
    __tablename__ = "routing_decisions"

    decision_id = Column(String(64), primary_key=True)
    issue_id = Column(String(64), ForeignKey("master_issues.id"), nullable=False, index=True)
    jurisdiction_id = Column(String(64), nullable=False, default="GLOBAL", index=True)
    category = Column(String(64), nullable=False)
    subcategory = Column(String(64), nullable=False)
    primary_department = Column(String(128), nullable=False, index=True)
    secondary_departments_json = Column(JSON, nullable=True)
    routing_rule_id = Column(String(64), nullable=False)
    routing_reasons_json = Column(JSON, nullable=False)
    confidence_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


# =====================================================================
# F & G. SLA Policies & Historical Snapshots
# =====================================================================
class SLAPolicyModel(Base):
    __tablename__ = "sla_policies"

    policy_id = Column(String(64), primary_key=True)
    jurisdiction_id = Column(String(64), nullable=True, index=True)
    category = Column(String(64), nullable=False)
    subcategory = Column(String(64), nullable=True)
    priority_level = Column(String(32), nullable=False)
    acknowledgement_minutes = Column(Integer, nullable=False)
    resolution_minutes = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="PROVISIONAL")
    source_reference = Column(String(128), nullable=True)
    source_title = Column(String(256), nullable=True)
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


# =====================================================================
# H & I. Issue Lifecycle & Append-Only History / Escalations
# =====================================================================
class IssueLifecycleModel(Base):
    __tablename__ = "issue_lifecycles"

    issue_id = Column(String(64), ForeignKey("master_issues.id"), primary_key=True)
    current_status = Column(String(32), nullable=False, default="REGISTERED", index=True)
    current_department = Column(String(128), nullable=False, index=True)
    jurisdiction_id = Column(String(64), nullable=False, default="GLOBAL", index=True)
    reopened_count = Column(Integer, nullable=False, default=0)
    is_overdue = Column(Boolean, nullable=False, default=False)
    sla_snapshot_json = Column(JSON, nullable=False)
    status_history_json = Column(JSON, nullable=False)
    escalation_history_json = Column(JSON, nullable=False)
    idempotency_replay = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class ReopenPolicyModel(Base):
    __tablename__ = "reopen_policies"

    policy_id = Column(String(64), primary_key=True)
    jurisdiction_id = Column(String(64), nullable=True, index=True)
    category = Column(String(64), nullable=True)
    reopen_threshold = Column(Integer, nullable=False, default=3)
    status = Column(String(32), nullable=False, default="PROVISIONAL")
    effective_from = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class ReopenIdempotencyModel(Base):
    __tablename__ = "reopen_idempotency_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(String(64), ForeignKey("master_issues.id"), nullable=False, index=True)
    idempotency_key = Column(String(128), nullable=False)
    replay_response_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    __table_args__ = (
        UniqueConstraint("issue_id", "idempotency_key", name="uq_reopen_idempotency"),
    )


# =====================================================================
# J & K. Work Assignments & Evidence Metadata
# =====================================================================
class WorkAssignmentModel(Base):
    __tablename__ = "work_assignments"

    assignment_id = Column(String(64), primary_key=True)
    issue_id = Column(String(64), ForeignKey("master_issues.id"), nullable=False, index=True)
    department = Column(String(128), nullable=False)
    unit_id = Column(String(64), nullable=False)
    operator_id = Column(String(64), nullable=False)
    assigned_by = Column(String(64), nullable=False)
    notes = Column(Text, nullable=True)
    assigned_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class EvidenceRecordModel(Base):
    __tablename__ = "evidence_records"

    evidence_id = Column(String(64), primary_key=True)
    issue_id = Column(String(64), ForeignKey("master_issues.id"), nullable=False, index=True)
    uploader_id = Column(String(64), nullable=False)
    file_name = Column(String(256), nullable=False)
    file_type = Column(String(32), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    sha256_checksum = Column(String(64), nullable=False)
    exif_sanitized = Column(Boolean, nullable=False, default=True)
    public_token = Column(String(64), nullable=False)
    evidence_type = Column(String(32), nullable=True, default="AFTER_IMAGE")
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class EvidenceVerificationModel(Base):
    __tablename__ = "evidence_verifications"

    verification_id = Column(String(64), primary_key=True)
    evidence_id = Column(String(64), ForeignKey("evidence_records.evidence_id"), nullable=False, index=True)
    issue_id = Column(String(64), ForeignKey("master_issues.id"), nullable=False, index=True)
    supervisor_id = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)  # APPROVED or REJECTED
    rejection_reason = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


# =====================================================================
# M, N, O, P, Q. RAG Documents, Chunks, Embeddings & Audit Logs
# =====================================================================
class RAGDocumentModel(Base):
    __tablename__ = "rag_documents"

    document_id = Column(String(64), primary_key=True)
    title = Column(String(256), nullable=False)
    issuing_authority = Column(String(128), nullable=False)
    jurisdiction_id = Column(String(64), nullable=True, index=True)
    document_type = Column(String(32), nullable=False)
    authority_status = Column(String(32), nullable=False, default="AUTHORITATIVE")
    access_level = Column(String(32), nullable=False, default="PUBLIC", index=True)
    source_reference = Column(String(128), nullable=True)
    source_title = Column(String(256), nullable=True)
    current_version_id = Column(String(64), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class RAGDocumentVersionModel(Base):
    __tablename__ = "rag_document_versions"

    version_id = Column(String(64), primary_key=True)
    document_id = Column(String(64), ForeignKey("rag_documents.document_id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    file_name = Column(String(256), nullable=False)
    sha256_checksum = Column(String(64), nullable=False)
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class RAGChunkModel(Base):
    __tablename__ = "rag_chunks"

    chunk_id = Column(String(64), primary_key=True)
    document_id = Column(String(64), ForeignKey("rag_documents.document_id"), nullable=False, index=True)
    version_id = Column(String(64), ForeignKey("rag_document_versions.version_id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    section_title = Column(String(256), nullable=True)
    page_number = Column(Integer, nullable=True)
    content_text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False)
    jurisdiction_id = Column(String(64), nullable=True, index=True)
    authority_status = Column(String(32), nullable=False)
    access_level = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class RAGEmbeddingModel(Base):
    __tablename__ = "rag_embeddings"

    chunk_id = Column(String(64), ForeignKey("rag_chunks.chunk_id"), primary_key=True)
    dimensions = Column(Integer, nullable=False, default=3072)
    vector_json = Column(JSON, nullable=False)  # 3072-dimensional vector payload


class RAGAuditLogModel(Base):
    __tablename__ = "rag_audit_logs"

    log_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=True)
    access_level = Column(String(32), nullable=False)
    query_text = Column(Text, nullable=False)
    evidence_found = Column(Boolean, nullable=False)
    answer_text = Column(Text, nullable=False)
    citations_json = Column(JSON, nullable=False)
    executed_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


# =====================================================================
# R, S, T, U. Hotspots, Opportunities, Proposals & Evidence Panels
# =====================================================================
class CivicHotspotModel(Base):
    __tablename__ = "civic_hotspots"

    hotspot_id = Column(String(64), primary_key=True)
    jurisdiction_id = Column(String(64), nullable=True, index=True)
    ward_name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False)
    center_latitude = Column(Float, nullable=False)
    center_longitude = Column(Float, nullable=False)
    radius_meters = Column(Integer, nullable=False, default=500)
    master_issue_count = Column(Integer, nullable=False)
    citizen_report_count = Column(Integer, nullable=False)
    severity_score_weighted = Column(Float, nullable=False)
    vulnerable_location_near = Column(Boolean, nullable=False, default=False)
    suppressed_publicly = Column(Boolean, nullable=False, default=False)
    linked_master_issue_ids_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class CivicProjectOpportunityModel(Base):
    __tablename__ = "civic_project_opportunities"

    opportunity_id = Column(String(64), primary_key=True)
    jurisdiction_id = Column(String(64), nullable=True, index=True)
    title = Column(String(256), nullable=False)
    category = Column(String(64), nullable=False)
    hotspot_id = Column(String(64), ForeignKey("civic_hotspots.hotspot_id"), nullable=True)
    linked_master_issue_ids_json = Column(JSON, nullable=False)
    total_citizen_reports = Column(Integer, nullable=False)
    estimated_priority_avg = Column(Float, nullable=False)
    status = Column(String(32), nullable=False, default="DETECTED")
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class CitizenProposalModel(Base):
    __tablename__ = "citizen_proposals"

    proposal_id = Column(String(64), primary_key=True)
    opportunity_id = Column(String(64), ForeignKey("civic_project_opportunities.opportunity_id"), nullable=True)
    jurisdiction_id = Column(String(64), nullable=False, default="WARD_7", index=True)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    proposer_id_hash = Column(String(64), nullable=False)
    category = Column(String(64), nullable=False)
    requested_budget = Column(Float, nullable=False)
    cost_status = Column(String(32), nullable=False, default="ESTIMATED")
    linked_master_issue_ids_json = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False, default="DRAFT", index=True)
    ai_generated_draft = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class ProposalEvidencePanelModel(Base):
    __tablename__ = "proposal_evidence_panels"

    proposal_id = Column(String(64), ForeignKey("citizen_proposals.proposal_id"), primary_key=True)
    linked_master_issues_json = Column(JSON, nullable=False)
    total_citizen_reports = Column(Integer, nullable=False, default=0)
    safety_risk_count = Column(Integer, nullable=False, default=0)
    historical_reopening_avg = Column(Float, nullable=False, default=0.0)
    rag_citations_json = Column(JSON, nullable=False)


# =====================================================================
# V, W, X, Y, Z. Finance, Budget Cycles, Voting, Scoring & Allocation
# =====================================================================
class CostEstimateLineItemModel(Base):
    __tablename__ = "cost_estimate_line_items"

    estimate_id = Column(String(64), primary_key=True)
    proposal_id = Column(String(64), ForeignKey("citizen_proposals.proposal_id"), nullable=False, index=True)
    unit_item_name = Column(String(128), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_rate = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    provenance = Column(String(32), nullable=False, default="PROVISIONAL")
    rate_table_ref = Column(String(128), nullable=True)
    created_by = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class BudgetCycleModel(Base):
    __tablename__ = "budget_cycles"

    cycle_id = Column(String(64), primary_key=True)
    jurisdiction_id = Column(String(64), nullable=False, index=True)
    cycle_name = Column(String(128), nullable=False)
    total_budget = Column(Float, nullable=False)
    min_project_cost = Column(Float, nullable=False, default=100000.0)
    max_project_cost = Column(Float, nullable=False, default=1000000.0)
    voting_start_time = Column(DateTime(timezone=True), nullable=False)
    voting_end_time = Column(DateTime(timezone=True), nullable=False)
    max_votes_per_citizen = Column(Integer, nullable=False, default=3)
    status = Column(String(32), nullable=False, default="ACTIVE_VOTING", index=True)
    active = Column(Boolean, nullable=False, default=True)


class ProposalEligibilityModel(Base):
    __tablename__ = "proposal_eligibilities"

    eligibility_id = Column(String(64), primary_key=True)
    proposal_id = Column(String(64), ForeignKey("citizen_proposals.proposal_id"), nullable=False, index=True)
    cycle_id = Column(String(64), ForeignKey("budget_cycles.cycle_id"), nullable=False)
    is_eligible = Column(Boolean, nullable=False)
    rule_results_json = Column(JSON, nullable=False)
    evaluation_notes = Column(Text, nullable=False)
    evaluated_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class VoterCredentialModel(Base):
    __tablename__ = "voter_credentials"

    voter_token_hash = Column(String(64), primary_key=True)
    cycle_id = Column(String(64), ForeignKey("budget_cycles.cycle_id"), nullable=False, index=True)
    jurisdiction_id = Column(String(64), nullable=False)
    votes_cast_count = Column(Integer, nullable=False, default=0)
    issued_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class VoteModel(Base):
    __tablename__ = "votes"

    vote_id = Column(String(64), primary_key=True)
    cycle_id = Column(String(64), ForeignKey("budget_cycles.cycle_id"), nullable=False, index=True)
    proposal_id = Column(String(64), ForeignKey("citizen_proposals.proposal_id"), nullable=False, index=True)
    voter_token_hash = Column(String(64), ForeignKey("voter_credentials.voter_token_hash"), nullable=False)
    jurisdiction_id = Column(String(64), nullable=False)
    voted_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

    __table_args__ = (
        UniqueConstraint("cycle_id", "voter_token_hash", "proposal_id", name="uq_cycle_voter_proposal"),
    )


class ProposalScoreModel(Base):
    __tablename__ = "proposal_scores"

    proposal_id = Column(String(64), ForeignKey("citizen_proposals.proposal_id"), primary_key=True)
    cycle_id = Column(String(64), ForeignKey("budget_cycles.cycle_id"), nullable=False, index=True)
    need_score = Column(Float, nullable=False)
    affected_population_score = Column(Float, nullable=False)
    safety_impact_score = Column(Float, nullable=False)
    recurrence_score = Column(Float, nullable=False)
    vulnerability_score = Column(Float, nullable=False)
    community_support_score = Column(Float, nullable=False)
    final_score = Column(Float, nullable=False, index=True)
    score_breakdown_json = Column(JSON, nullable=False)
    calculated_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class BudgetAllocationModel(Base):
    __tablename__ = "budget_allocations"

    allocation_id = Column(String(64), primary_key=True)
    cycle_id = Column(String(64), ForeignKey("budget_cycles.cycle_id"), nullable=False, index=True)
    total_budget = Column(Float, nullable=False)
    allocated_budget = Column(Float, nullable=False)
    remaining_budget = Column(Float, nullable=False)
    selected_proposals_json = Column(JSON, nullable=False)
    rejected_proposals_json = Column(JSON, nullable=False)
    decision_log_json = Column(JSON, nullable=False)
    allocated_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


# =====================================================================
# Auth & User Account Persistence
# =====================================================================
class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False, default="CITIZEN", index=True)
    jurisdiction_id = Column(String(64), nullable=False, default="GLOBAL")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

