from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.taxonomy import Category


class PriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FactorDetail(BaseModel):
    raw_value: Any
    max_value: Optional[Any] = None
    normalized_score: float = Field(..., description="Score normalized from 0.0 to 100.0")
    weight: float = Field(..., description="Component weight in formula")
    contribution: float = Field(..., description="Contribution to base score before modifiers")


class VulnerableLocationFactorDetail(BaseModel):
    multiplier: float = Field(default=1.0, ge=1.0, le=1.50)
    nearby_sensitive_assets: List[Dict[str, Any]] = Field(default_factory=list)


class CitizenReportsFactorDetail(BaseModel):
    report_count: int = Field(default=1, ge=1)
    boost_score: float = Field(default=0.0)
    boost_applied: float = Field(default=0.0)


class DurationFactorDetail(BaseModel):
    hours_unresolved: float = Field(default=0.0, ge=0.0)
    boost_applied: float = Field(default=0.0)


class PriorityFactorsBreakdown(BaseModel):
    severity: FactorDetail
    safety_risk: FactorDetail
    public_impact: FactorDetail
    category_baseline: FactorDetail
    vulnerable_location: VulnerableLocationFactorDetail
    citizen_reports: CitizenReportsFactorDetail
    duration: DurationFactorDetail


class PriorityCalculateRequest(BaseModel):
    issue_id: Optional[str] = Field(default=None, description="Optional issue UUID for tracking")
    severity: int = Field(..., ge=0, le=5, description="Severity score 0 to 5")
    safety_risk: bool = Field(..., description="True if safety hazard identified")
    public_impact: int = Field(..., ge=0, le=5, description="Public impact rating 0 to 5")
    category: Category = Field(..., description="Issue category")
    subcategory: str = Field(..., description="Issue subcategory")
    citizen_reporter_count: int = Field(default=1, ge=1, description="Merged citizen report count")
    hours_unresolved: float = Field(default=0.0, ge=0.0, description="Hours since issue reported")
    latitude: Optional[float] = Field(default=None, description="Latitude for GIS spatial vulnerable location calculation")
    longitude: Optional[float] = Field(default=None, description="Longitude for GIS spatial vulnerable location calculation")


class PriorityAssessmentResult(BaseModel):
    issue_id: str
    priority_score: int = Field(..., ge=0, le=100, description="Final explainable priority score 0 to 100")
    priority_level: PriorityLevel
    calculated_at: str
    formula_version: str = "v1.0.0"
    factors: PriorityFactorsBreakdown
    score_computation_log: str = Field(..., description="Human-readable step-by-step formula execution log")
