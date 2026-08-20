from enum import Enum
from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from app.taxonomy import Category, CATEGORIES_LIST, TAXONOMY_SUBCATEGORIES


class ConfidenceStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


class Severity(BaseModel):
    score: int = Field(..., ge=0, le=5, description="Severity integer from 0 to 5")


class LocationInformation(BaseModel):
    location_description: Optional[str] = Field(
        default=None, description="Extracted location details from text, e.g. near the school"
    )


class Classification(BaseModel):
    category: Category = Field(..., description="Primary category of the civic issue")
    subcategory: str = Field(..., description="Specific subcategory for the issue")
    severity: int = Field(..., ge=0, le=5, description="Severity rating from 0 (minor) to 5 (critical)")
    safety_risk: bool = Field(..., description="True if there is an immediate safety hazard")
    public_impact: int = Field(..., ge=0, le=5, description="Public impact score from 0 to 5")
    location_description: Optional[str] = Field(default="", description="Location details if mentioned in text")
    summary: str = Field(..., description="Concise issue summary")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score between 0.0 and 1.0")

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v):
        if isinstance(v, str):
            v_upper = v.upper().strip()
            if v_upper not in CATEGORIES_LIST:
                raise ValueError(
                    f"Invalid category '{v}'. Category must be one of: {sorted(list(CATEGORIES_LIST))}"
                )
            return Category(v_upper)
        return v

    @field_validator("subcategory", mode="before")
    @classmethod
    def validate_subcategory(cls, v):
        if isinstance(v, str):
            return v.upper().strip()
        return v

    @field_validator("subcategory", mode="after")
    @classmethod
    def enforce_taxonomy_subcategory(cls, v: str, info) -> str:
        category = info.data.get("category")
        if category and isinstance(category, Category):
            valid_subs = TAXONOMY_SUBCATEGORIES.get(category.value, ["OTHER"])
            if v not in valid_subs:
                return "OTHER"
        return v


class ComplaintAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw complaint text submitted by user")


class ComplaintAnalysis(BaseModel):
    original_text: str
    original_language: str
    normalized_text: str
    language: str
    category: Category
    subcategory: str
    severity: int = Field(..., ge=0, le=5)
    safety_risk: bool
    public_impact: int = Field(..., ge=0, le=5)
    location_description: Optional[str] = ""
    detailed_description: Optional[str] = ""
    summary: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_status: ConfidenceStatus
    language_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Dedicated language detector confidence")
    language_detector: str = Field(default="unicode_script_heuristic", description="Name of language detector used")
    language_disagreement: bool = Field(default=False, description="True if LLM and dedicated language detector disagreed")


class TranscriptionResult(BaseModel):
    text: str = Field(..., description="Transcribed audio text")
    language: str = Field(..., description="Detected transcription language code")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Transcription confidence score")
    provider: str = Field(..., description="Name of STT provider used")


class AudioComplaintAnalysisResponse(BaseModel):
    input_type: Literal["audio"] = "audio"
    transcription: TranscriptionResult
    analysis: ComplaintAnalysis


class VisualAnalysis(BaseModel):
    visible_issue: bool = Field(..., description="True if a civic issue is visually identified in the image")
    category: Category = Field(..., description="Visual category from taxonomy")
    subcategory: str = Field(..., description="Visual subcategory")
    severity: int = Field(..., ge=0, le=5, description="Visual severity from 0 to 5")
    safety_risk: bool = Field(..., description="True if visual evidence indicates immediate safety risk")
    public_impact: int = Field(..., ge=0, le=5, description="Visual public impact score from 0 to 5")
    description: str = Field(..., description="Detailed visual description of visible scene and civic issue")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Visual extraction confidence score")

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v):
        if isinstance(v, str):
            v_upper = v.upper().strip()
            if v_upper not in CATEGORIES_LIST:
                return Category.OTHER
            return Category(v_upper)
        return v


class ImageComplaintAnalysisResponse(BaseModel):
    input_type: Literal["image"] = "image"
    visual_analysis: VisualAnalysis
    analysis: ComplaintAnalysis
    evidence_disagreement: bool = Field(default=False, description="True if visual evidence conflicts with accompanying text")
    disagreement_reason: Optional[str] = Field(default=None, description="Explanation of disagreement if evidence_disagreement is true")


class DuplicateAction(str, Enum):
    AUTOMATIC_MERGE = "AUTOMATIC_MERGE"
    HUMAN_REVIEW_RECOMMENDED = "HUMAN_REVIEW_RECOMMENDED"
    NEW_MASTER_ISSUE = "NEW_MASTER_ISSUE"


class DuplicateReviewDecisionEnum(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class MasterIssueModel(BaseModel):
    id: str = Field(..., description="Unique Master Issue UUID")
    title: str = Field(..., description="Canonical summary title")
    category: Category = Field(..., description="Category enum")
    subcategory: str = Field(..., description="Subcategory string")
    status: str = Field(default="OPEN", description="Cluster status: OPEN, IN_PROGRESS, RESOLVED")
    severity_score: int = Field(..., ge=0, le=5)
    citizen_reporter_count: int = Field(default=1, description="Total citizen reports merged into this issue")
    latitude: float = Field(..., description="Geographic centroid latitude")
    longitude: float = Field(..., description="Geographic centroid longitude")
    address_description: Optional[str] = ""
    description: Optional[str] = ""
    department: Optional[str] = Field(default=None, description="Assigned department")
    priority_level: Optional[str] = Field(default=None, description="Calculated priority level: CRITICAL, HIGH, MEDIUM, LOW")
    is_overdue: Optional[bool] = Field(default=False, description="True if resolution deadline has passed")
    created_at: str = Field(..., description="Timestamp ISO string")


class DuplicateCheckRequest(BaseModel):
    complaint_id: Optional[str] = Field(default=None, description="Optional unique citizen complaint UUID for idempotency")
    text: str = Field(..., min_length=1, description="Complaint text description")
    category: Category
    subcategory: str
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    severity: int = Field(default=3, description="Initial severity AI prediction")
    safety_risk: bool = Field(default=False, description="Initial safety risk AI prediction")
    description: str = Field(default="", description="Detailed issue description")
    image_embedding: Optional[List[float]] = None


class ScoreBreakdown(BaseModel):
    geographic_distance_meters: float = Field(..., description="Distance in meters to master centroid")
    spatial_score: float = Field(..., ge=0.0, le=1.0)
    semantic_similarity: float = Field(..., ge=0.0, le=1.0)
    category_match_score: float = Field(..., ge=0.0, le=1.0)
    temporal_score: float = Field(..., ge=0.0, le=1.0)
    total_score: float = Field(..., ge=0.0, le=1.0)
    normalized_weights_used: bool = Field(default=False, description="True if available-signal weight normalization was applied")


class DuplicateCheckResponse(BaseModel):
    action: DuplicateAction
    matched_master_issue_id: Optional[str] = None
    master_issue: Optional[MasterIssueModel] = None
    total_score: float = Field(..., ge=0.0, le=1.0)
    score_breakdown: ScoreBreakdown
    citizen_reporter_count: int = Field(default=1)
    review_id: Optional[str] = Field(default=None, description="ID of queued duplicate review if action is HUMAN_REVIEW_RECOMMENDED")


class DuplicateReviewRecordModel(BaseModel):
    review_id: str
    complaint_id: str
    candidate_master_issue_id: str
    similarity_score: float
    score_breakdown: ScoreBreakdown
    status: str = Field(default="PENDING", description="PENDING, APPROVED, REJECTED")
    operator_id: Optional[str] = None
    created_at: str
    resolved_at: Optional[str] = None


class DuplicateReviewDecisionRequest(BaseModel):
    review_id: str = Field(..., description="Review UUID to resolve")
    decision: DuplicateReviewDecisionEnum = Field(..., description="APPROVED or REJECTED")
    operator_id: Optional[str] = Field(default="operator_1", description="ID of municipal operator making decision")


class AcknowledgeIssueRequest(BaseModel):
    operator_id: str = Field(default="operator_1", description="ID of operator acknowledging ticket")
    notes: Optional[str] = Field(default=None, description="Optional acknowledgement notes")


class EscalateIssueRequest(BaseModel):
    target_department: Optional[str] = Field(default=None, description="Optional explicit escalation target department")
    reason: str = Field(default="OPERATOR_ESCALATED", description="Reason for escalation")
    operator_id: Optional[str] = Field(default="operator_1", description="ID of operator escalating ticket")
    notes: Optional[str] = Field(default=None, description="Optional escalation notes")


class ReopenIssueRequest(BaseModel):
    actor_id: str = Field(default="citizen_1", description="ID of citizen or supervisor reopening ticket")
    reason: str = Field(default="Dissatisfied with work", description="Reason for reopening issue")
    notes: Optional[str] = Field(default=None, description="Optional reopening details")
    idempotency_key: Optional[str] = Field(default=None, description="Optional unique key for idempotent reopen requests")



class SubmitCompletionRequest(BaseModel):
    operator_id: str = Field(default="operator_1", description="ID of operator submitting work completion")
    notes: Optional[str] = Field(default=None, description="Optional completion notes")


class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: Optional[str] = None


class LocationClues(BaseModel):
    village_locality: Optional[str] = Field(default=None, description="Village or locality name if present")
    ward: Optional[str] = Field(default=None, description="Ward number or name if present")
    road_street: Optional[str] = Field(default=None, description="Road or street name if present")
    landmark: Optional[str] = Field(default=None, description="Prominent landmark (school, hospital, bus stop, market, etc.)")
    city_district: Optional[str] = Field(default=None, description="City or district if mentioned")
    raw_query: str = Field(..., description="Synthesized search query combining the most confident clues for geocoding")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the extracted location details")


class CandidateLocation(BaseModel):
    display_name: str
    latitude: float
    longitude: float
    confidence: float
    is_in_jurisdiction: bool = True
    source: Optional[str] = None


class LocationExtractionRequest(BaseModel):
    text: str = Field(..., min_length=1)


class LocationExtractionResponse(BaseModel):
    clues: LocationClues
    candidates: List[CandidateLocation]


class AudioTranscriptionResponse(BaseModel):
    input_type: Literal["audio"] = "audio"
    transcription: TranscriptionResult


# =====================================================================
# Auth Schemas
# =====================================================================
class UserRoleEnum(str, Enum):
    CITIZEN = "CITIZEN"
    OPERATOR = "OPERATOR"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"


class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, description="User email")
    password: str = Field(..., min_length=6, description="User password")
    full_name: str = Field(..., min_length=1, description="Full name")
    role: UserRoleEnum = Field(default=UserRoleEnum.CITIZEN)
    jurisdiction_id: Optional[str] = Field(default="GLOBAL")


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRoleEnum
    jurisdiction_id: str
    is_active: bool
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


