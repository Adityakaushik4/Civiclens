import math
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional
from app.taxonomy import Category
from app.gis.vulnerability import vulnerable_location_evaluator
from app.priority.schemas import (
    PriorityLevel,
    FactorDetail,
    VulnerableLocationFactorDetail,
    CitizenReportsFactorDetail,
    DurationFactorDetail,
    PriorityFactorsBreakdown,
    PriorityCalculateRequest,
    PriorityAssessmentResult,
)

CATEGORY_BASELINE_SCORES: Dict[str, float] = {
    Category.ELECTRICITY.value: 90.0,
    Category.SEWERAGE.value: 90.0,
    Category.WATER_SUPPLY.value: 90.0,
    Category.ROAD_DAMAGE.value: 75.0,
    Category.DRAINAGE.value: 75.0,
    Category.STREETLIGHT.value: 75.0,
    Category.GARBAGE.value: 60.0,
    Category.TRAFFIC.value: 60.0,
    Category.PUBLIC_TOILET.value: 40.0,
    Category.PARK.value: 40.0,
    Category.OTHER.value: 20.0,
}


class PriorityStore:
    """In-memory store for Priority Assessment records."""

    def __init__(self):
        self._assessments: Dict[str, PriorityAssessmentResult] = {}

    def save(self, result: PriorityAssessmentResult) -> None:
        self._assessments[result.issue_id] = result

    def get(self, issue_id: str) -> Optional[PriorityAssessmentResult]:
        return self._assessments.get(issue_id)

    def clear(self) -> None:
        self._assessments.clear()


priority_store = PriorityStore()


class PriorityCalculator:
    """Deterministic, explainable priority calculation engine."""

    WEIGHT_SEVERITY = 0.35
    WEIGHT_SAFETY_RISK = 0.25
    WEIGHT_PUBLIC_IMPACT = 0.20
    WEIGHT_CATEGORY_BASELINE = 0.20

    def calculate_priority(self, request: PriorityCalculateRequest) -> PriorityAssessmentResult:
        issue_id = request.issue_id or f"issue_{uuid.uuid4().hex[:8]}"

        # 1. Severity sub-score
        sev_normalized = (request.severity / 5.0) * 100.0
        sev_contrib = sev_normalized * self.WEIGHT_SEVERITY
        sev_detail = FactorDetail(
            raw_value=request.severity,
            max_value=5,
            normalized_score=round(sev_normalized, 2),
            weight=self.WEIGHT_SEVERITY,
            contribution=round(sev_contrib, 2),
        )

        # 2. Safety Risk sub-score
        safe_normalized = 100.0 if request.safety_risk else 0.0
        safe_contrib = safe_normalized * self.WEIGHT_SAFETY_RISK
        safe_detail = FactorDetail(
            raw_value=request.safety_risk,
            max_value=True,
            normalized_score=round(safe_normalized, 2),
            weight=self.WEIGHT_SAFETY_RISK,
            contribution=round(safe_contrib, 2),
        )

        # 3. Public Impact sub-score
        impact_normalized = (request.public_impact / 5.0) * 100.0
        impact_contrib = impact_normalized * self.WEIGHT_PUBLIC_IMPACT
        impact_detail = FactorDetail(
            raw_value=request.public_impact,
            max_value=5,
            normalized_score=round(impact_normalized, 2),
            weight=self.WEIGHT_PUBLIC_IMPACT,
            contribution=round(impact_contrib, 2),
        )

        # 4. Category Baseline sub-score
        cat_key = request.category.value if isinstance(request.category, Category) else str(request.category)
        cat_baseline = CATEGORY_BASELINE_SCORES.get(cat_key, 20.0)
        cat_contrib = cat_baseline * self.WEIGHT_CATEGORY_BASELINE
        cat_detail = FactorDetail(
            raw_value=cat_key,
            max_value=100.0,
            normalized_score=round(cat_baseline, 2),
            weight=self.WEIGHT_CATEGORY_BASELINE,
            contribution=round(cat_contrib, 2),
        )

        # 5. Base score sum (0 to 100)
        base_score = sev_contrib + safe_contrib + impact_contrib + cat_contrib

        # 6. GIS Vulnerable Location Multiplier
        if request.latitude is not None and request.longitude is not None:
            vuln_multiplier, nearby_assets = vulnerable_location_evaluator.calculate_vulnerability_factor(
                request.latitude, request.longitude
            )
        else:
            vuln_multiplier, nearby_assets = 1.0, []

        vuln_detail = VulnerableLocationFactorDetail(
            multiplier=round(vuln_multiplier, 4),
            nearby_sensitive_assets=nearby_assets,
        )

        base_score_modified = base_score * vuln_multiplier

        # 7. Citizen Reports Logarithmic Boost
        report_count = max(1, request.citizen_reporter_count)
        raw_report_boost = 8.0 * math.log2(report_count)
        applied_report_boost = min(20.0, raw_report_boost)
        reports_detail = CitizenReportsFactorDetail(
            report_count=report_count,
            boost_score=round(raw_report_boost, 2),
            boost_applied=round(applied_report_boost, 2),
        )

        # 8. Duration Unresolved Boost
        hours = max(0.0, request.hours_unresolved)
        applied_duration_boost = min(15.0, (hours / 24.0) * 2.5)
        duration_detail = DurationFactorDetail(
            hours_unresolved=round(hours, 2),
            boost_applied=round(applied_duration_boost, 2),
        )

        # 9. Final Score Calculation
        total_raw = base_score_modified + applied_report_boost + applied_duration_boost
        final_score = int(round(min(100.0, max(0.0, total_raw))))

        # 10. Determine Priority Level
        if final_score >= 80:
            level = PriorityLevel.CRITICAL
        elif final_score >= 60:
            level = PriorityLevel.HIGH
        elif final_score >= 35:
            level = PriorityLevel.MEDIUM
        else:
            level = PriorityLevel.LOW

        factors = PriorityFactorsBreakdown(
            severity=sev_detail,
            safety_risk=safe_detail,
            public_impact=impact_detail,
            category_baseline=cat_detail,
            vulnerable_location=vuln_detail,
            citizen_reports=reports_detail,
            duration=duration_detail,
        )

        log = (
            f"Base Score = ({sev_contrib:.2f} + {safe_contrib:.2f} + {impact_contrib:.2f} + {cat_contrib:.2f}) = {base_score:.2f}. "
            f"Vuln Multiplier ({vuln_multiplier:.2f}x) -> {base_score_modified:.2f}. "
            f"Report Boost (+{applied_report_boost:.2f}), Duration Boost (+{applied_duration_boost:.2f}) -> "
            f"Raw Total = {total_raw:.2f} -> Final Clamped Score = {final_score} [{level.value}]"
        )

        result = PriorityAssessmentResult(
            issue_id=issue_id,
            priority_score=final_score,
            priority_level=level,
            calculated_at=datetime.now(timezone.utc).isoformat(),
            formula_version="v1.0.0",
            factors=factors,
            score_computation_log=log,
        )

        # Store result in priority store
        priority_store.save(result)
        return result


priority_calculator = PriorityCalculator()
