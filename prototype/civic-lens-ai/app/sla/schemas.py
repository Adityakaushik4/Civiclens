import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, model_validator
from app.priority.schemas import PriorityLevel
from app.taxonomy import CATEGORIES_LIST, TAXONOMY_SUBCATEGORIES, Category


class SLAPolicyStatus(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    AUTHORITATIVE = "AUTHORITATIVE"
    INACTIVE = "INACTIVE"


class SLAPolicy(BaseModel):
    policy_id: str = Field(..., description="Unique policy UUID or key identifier")
    jurisdiction_id: Optional[str] = Field(default=None, description="Optional target jurisdiction / city ID")
    category: str = Field(..., description="Target category or '*' for global")
    subcategory: Optional[str] = Field(default=None, description="Target subcategory or '*' or null")
    priority_level: PriorityLevel = Field(..., description="Target priority level")
    acknowledgement_minutes: int = Field(..., description="Response/acknowledgement SLA in minutes")
    resolution_minutes: int = Field(..., description="Resolution SLA in minutes")
    status: SLAPolicyStatus = Field(default=SLAPolicyStatus.PROVISIONAL, description="PROVISIONAL, AUTHORITATIVE, INACTIVE")
    source_reference: Optional[str] = Field(default=None, description="Legal act, charter section, or reference URL")
    source_title: Optional[str] = Field(default=None, description="Title of official policy document")
    effective_from: Optional[str] = Field(default=None, description="ISO timestamp from which policy applies")
    effective_until: Optional[str] = Field(default=None, description="ISO timestamp until which policy applies")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    active: bool = Field(default=True, description="True if policy is active")

    @model_validator(mode="after")
    def validate_policy_rules(self) -> "SLAPolicy":
        # 1. acknowledgement_minutes > 0
        if self.acknowledgement_minutes <= 0:
            raise ValueError("acknowledgement_minutes must be greater than 0.")

        # 2. resolution_minutes > acknowledgement_minutes
        if self.resolution_minutes <= self.acknowledgement_minutes:
            raise ValueError("resolution_minutes must be greater than acknowledgement_minutes.")

        # 3. Authoritative provenance rule
        if self.status == SLAPolicyStatus.AUTHORITATIVE:
            if not self.source_reference or not self.source_reference.strip():
                raise ValueError("An AUTHORITATIVE SLA policy must provide a non-empty source_reference.")

        # 4. Effective dates ordering
        if self.effective_from and self.effective_until:
            if self.effective_from > self.effective_until:
                raise ValueError("effective_from timestamp cannot be after effective_until timestamp.")

        # 5. Taxonomy validation
        cat_upper = self.category.strip().upper() if self.category else "*"
        if cat_upper != "*" and cat_upper not in CATEGORIES_LIST:
            raise ValueError(f"Invalid category '{self.category}'. Must be '*' or one of {sorted(list(CATEGORIES_LIST))}.")

        if self.subcategory and self.subcategory != "*":
            sub_upper = self.subcategory.strip().upper()
            if cat_upper != "*" and cat_upper in TAXONOMY_SUBCATEGORIES:
                valid_subs = TAXONOMY_SUBCATEGORIES[cat_upper]
                if sub_upper not in valid_subs and sub_upper != "OTHER":
                    raise ValueError(f"Invalid subcategory '{self.subcategory}' for category '{cat_upper}'. Valid options: {valid_subs}")

        return self


class SLAPolicyCreateRequest(BaseModel):
    policy_id: Optional[str] = Field(default=None, description="Optional custom policy ID")
    jurisdiction_id: Optional[str] = Field(default=None, description="Optional target jurisdiction / city ID")
    category: str = Field(..., description="Target category or '*'")
    subcategory: Optional[str] = Field(default=None, description="Target subcategory or '*'")
    priority_level: PriorityLevel = Field(..., description="Target priority level")
    acknowledgement_minutes: int = Field(..., description="Acknowledgement SLA in minutes")
    resolution_minutes: int = Field(..., description="Resolution SLA in minutes")
    status: SLAPolicyStatus = Field(default=SLAPolicyStatus.PROVISIONAL)
    source_reference: Optional[str] = Field(default=None)
    source_title: Optional[str] = Field(default=None)
    effective_from: Optional[str] = Field(default=None)
    effective_until: Optional[str] = Field(default=None)


class SLAPolicyUpdateRequest(BaseModel):
    jurisdiction_id: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    priority_level: Optional[PriorityLevel] = None
    acknowledgement_minutes: Optional[int] = None
    resolution_minutes: Optional[int] = None
    status: Optional[SLAPolicyStatus] = None
    source_reference: Optional[str] = None
    source_title: Optional[str] = None
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    active: Optional[bool] = None


class SLASnapshot(BaseModel):
    policy_id: str
    status: SLAPolicyStatus
    source_reference: Optional[str] = None
    source_title: Optional[str] = None
    acknowledgement_minutes: int
    resolution_minutes: int
    acknowledgement_deadline: str
    resolution_deadline: str
