from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyticsSummaryRequest(BaseModel):
    jurisdiction_id: Optional[str] = Field(default=None, description="Optional jurisdiction filter")
    category: Optional[str] = Field(default=None, description="Optional category filter")


class CivicAnalyticsSnapshot(BaseModel):
    snapshot_id: str
    jurisdiction_id: Optional[str] = None
    period_name: str
    total_master_issues: int
    total_citizen_reports: int
    total_issues_resolved: int = 0
    pending_verification_count: int = 0
    resolved_today_count: int = 0
    reopened_count: int = 0
    overdue_count: int = 0
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    department_distribution: Dict[str, int] = Field(default_factory=dict)
    priority_distribution: Dict[str, int] = Field(default_factory=dict)
    resolution_rate: float
    sla_breach_rate: float
    reopening_rate: float
    created_at: str


class CivicHotspot(BaseModel):
    hotspot_id: str
    jurisdiction_id: Optional[str] = None
    ward_name: str
    category: str
    center_latitude: float
    center_longitude: float
    radius_meters: int = 500
    master_issue_count: int
    citizen_report_count: int
    severity_score_weighted: float
    vulnerable_location_near: bool = False
    suppressed_publicly: bool = False  # Small-cell suppression if reports < 5
    linked_master_issue_ids: List[str] = Field(default_factory=list)
    created_at: str


class TemporalTrendPoint(BaseModel):
    period: str
    category: str
    issue_count: int
    report_count: int
    percentage_change: float
    trend_description: str
