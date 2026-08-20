from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class AuthorityStatus(str, Enum):
    AUTHORITATIVE = "AUTHORITATIVE"
    PROVISIONAL = "PROVISIONAL"
    INACTIVE = "INACTIVE"


class AccessLevel(str, Enum):
    PUBLIC = "PUBLIC"
    OPERATOR = "OPERATOR"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"


class DocumentType(str, Enum):
    POLICY = "POLICY"
    REGULATION = "REGULATION"
    BYLAW = "BYLAW"
    OPERATIONAL_GUIDELINE = "OPERATIONAL_GUIDELINE"


class CivicDocument(BaseModel):
    document_id: str
    title: str
    issuing_authority: str
    jurisdiction_id: Optional[str] = Field(default=None, description="Nullable for global/national policies")
    document_type: DocumentType = DocumentType.POLICY
    authority_status: AuthorityStatus = AuthorityStatus.PROVISIONAL
    access_level: AccessLevel = AccessLevel.PUBLIC
    source_reference: Optional[str] = None
    current_version_id: Optional[str] = None
    created_at: str
    updated_at: str


class DocumentVersion(BaseModel):
    version_id: str
    document_id: str
    version_number: int
    publication_date: Optional[str] = None
    effective_from: str
    effective_until: Optional[str] = None
    source_reference: str
    source_title: Optional[str] = None
    file_key: str
    file_name: str
    mime_type: str
    checksum: str
    ingested_by: str
    ingestion_timestamp: str
    active: bool = True


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    version_id: str
    chunk_index: int
    section_title: Optional[str] = None
    subsection_title: Optional[str] = None
    page_number: Optional[int] = None
    content_text: str
    token_count: int
    jurisdiction_id: Optional[str] = None
    authority_status: AuthorityStatus
    access_level: AccessLevel
    created_at: str


class ChunkEmbedding(BaseModel):
    embedding_id: str
    chunk_id: str
    model_name: str = "gemini-embedding-001"
    dimensions: int = 3072
    vector: List[float]


class Citation(BaseModel):
    document_title: str
    issuing_authority: str
    version: str
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    source_reference: str
    authority_status: AuthorityStatus
    chunk_id: str


class GroundedQARequest(BaseModel):
    query: str = Field(..., description="User question or knowledge query")
    jurisdiction_id: Optional[str] = Field(default=None, description="Filter for specific jurisdiction")
    access_level: AccessLevel = Field(default=AccessLevel.PUBLIC, description="Caller RBAC access level")
    top_k: int = Field(default=5, ge=1, le=20, description="Top-K candidate chunks to retrieve")


class GroundedQAResponse(BaseModel):
    query: str
    answer: str
    evidence_found: bool
    citations: List[Citation] = Field(default_factory=list)
    retrieved_chunks_count: int = 0


class DocumentIngestRequest(BaseModel):
    title: str = Field(..., description="Title of civic document")
    issuing_authority: str = Field(..., description="Municipal agency or issuing authority")
    jurisdiction_id: Optional[str] = Field(default=None, description="Optional target jurisdiction ID")
    document_type: DocumentType = Field(default=DocumentType.POLICY, description="Document type")
    authority_status: AuthorityStatus = Field(default=AuthorityStatus.PROVISIONAL, description="AUTHORITATIVE or PROVISIONAL")
    access_level: AccessLevel = Field(default=AccessLevel.PUBLIC, description="Minimum required RBAC level")
    source_reference: Optional[str] = Field(default=None, description="Required for AUTHORITATIVE status")
    source_title: Optional[str] = Field(default=None, description="Title of reference source")
    effective_from: Optional[str] = Field(default=None, description="Effective start ISO timestamp")
    effective_until: Optional[str] = Field(default=None, description="Effective end ISO timestamp")
