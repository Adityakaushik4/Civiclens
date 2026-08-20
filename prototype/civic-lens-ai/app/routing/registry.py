from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field
from app.taxonomy import Category, Department


class DepartmentMapping(BaseModel):
    category: str
    subcategory: str
    primary_department: str
    responsible_unit: str
    escalation_department: str
    baseline_priority: str = "MEDIUM"


class DepartmentRegistry:
    """Registry managing deterministic taxonomy mappings to municipal departments and units."""

    def __init__(self):
        self._subcategory_mappings: Dict[Tuple[str, str], DepartmentMapping] = {}
        self._category_mappings: Dict[str, DepartmentMapping] = {}
        self._seed_default_registry()

    def _seed_default_registry(self) -> None:
        # 1. Category-level Defaults
        cat_defaults = [
            DepartmentMapping(
                category=Category.ROAD_DAMAGE.value,
                subcategory="*",
                primary_department=Department.ROADS_PWD.value,
                responsible_unit="Asphalt Patching Unit",
                escalation_department="Dept of Public Works (DPW)",
                baseline_priority="MEDIUM",
            ),
            DepartmentMapping(
                category=Category.GARBAGE.value,
                subcategory="*",
                primary_department=Department.SANITATION_WASTE.value,
                responsible_unit="Solid Waste Management Unit",
                escalation_department="Director of Sanitation",
                baseline_priority="LOW",
            ),
            DepartmentMapping(
                category=Category.STREETLIGHT.value,
                subcategory="*",
                primary_department=Department.ELECTRICAL_LIGHTING.value,
                responsible_unit="Area Lighting Unit",
                escalation_department="Chief Electrical Officer",
                baseline_priority="LOW",
            ),
            DepartmentMapping(
                category=Category.DRAINAGE.value,
                subcategory="*",
                primary_department=Department.DRAINAGE_SEWERAGE.value,
                responsible_unit="Stormwater & Drain Unit",
                escalation_department="Dept of Public Works (DPW)",
                baseline_priority="HIGH",
            ),
            DepartmentMapping(
                category=Category.WATER_SUPPLY.value,
                subcategory="*",
                primary_department=Department.WATER_SUPPLY.value,
                responsible_unit="Pipe & Mains Crew",
                escalation_department="Ministry of Water Resources",
                baseline_priority="HIGH",
            ),
            DepartmentMapping(
                category=Category.SEWERAGE.value,
                subcategory="*",
                primary_department=Department.DRAINAGE_SEWERAGE.value,
                responsible_unit="Underground Utility Crew",
                escalation_department="Chief Municipal Engineer",
                baseline_priority="HIGH",
            ),
            DepartmentMapping(
                category=Category.ELECTRICITY.value,
                subcategory="*",
                primary_department=Department.ELECTRICAL_LIGHTING.value,
                responsible_unit="Power Grid Unit",
                escalation_department="Disaster Response Cell",
                baseline_priority="HIGH",
            ),
            DepartmentMapping(
                category=Category.PUBLIC_TOILET.value,
                subcategory="*",
                primary_department=Department.PUBLIC_TOILETS.value,
                responsible_unit="Facility Hygiene Crew",
                escalation_department="Municipal Health Officer",
                baseline_priority="LOW",
            ),
            DepartmentMapping(
                category=Category.PARK.value,
                subcategory="*",
                primary_department=Department.PARKS_HORTICULTURE.value,
                responsible_unit="Park Maintenance Crew",
                escalation_department="Director of Parks",
                baseline_priority="LOW",
            ),
            DepartmentMapping(
                category=Category.TRAFFIC.value,
                subcategory="*",
                primary_department=Department.TRAFFIC_SAFETY.value,
                responsible_unit="Signals & Signage Unit",
                escalation_department="Traffic Police Head Office",
                baseline_priority="MEDIUM",
            ),
            DepartmentMapping(
                category=Category.OTHER.value,
                subcategory="*",
                primary_department=Department.OTHER_GENERAL.value,
                responsible_unit="Customer Support Triage Unit",
                escalation_department="Municipal Secretary Office",
                baseline_priority="LOW",
            ),
        ]

        for mapping in cat_defaults:
            self._category_mappings[mapping.category] = mapping

        # 2. Specific Subcategory Specialized Rules
        sub_overrides = [
            DepartmentMapping(
                category=Category.STREETLIGHT.value,
                subcategory="EXPOSED_WIRING",
                primary_department=Department.ELECTRICAL_LIGHTING.value,
                responsible_unit="Rapid Hazard Electrical Crew",
                escalation_department="Chief Electrical Officer",
                baseline_priority="CRITICAL",
            ),
            DepartmentMapping(
                category=Category.SEWERAGE.value,
                subcategory="OPEN_MANHOLE",
                primary_department=Department.DRAINAGE_SEWERAGE.value,
                responsible_unit="Underground Utility Safety Unit",
                escalation_department="Chief Municipal Engineer",
                baseline_priority="CRITICAL",
            ),
            DepartmentMapping(
                category=Category.ELECTRICITY.value,
                subcategory="SPARKING",
                primary_department=Department.ELECTRICAL_LIGHTING.value,
                responsible_unit="High Tension Emergency Unit",
                escalation_department="Disaster Response Cell",
                baseline_priority="CRITICAL",
            ),
            DepartmentMapping(
                category=Category.WATER_SUPPLY.value,
                subcategory="CONTAMINATED_WATER",
                primary_department=Department.PUBLIC_HEALTH.value,
                responsible_unit="Public Health Water Quality Unit",
                escalation_department="Ministry of Water Resources",
                baseline_priority="CRITICAL",
            ),
            DepartmentMapping(
                category=Category.GARBAGE.value,
                subcategory="DEAD_ANIMAL",
                primary_department=Department.ANIMAL_CONTROL.value,
                responsible_unit="Animal Carcass Removal Unit",
                escalation_department="Municipal Health Officer",
                baseline_priority="HIGH",
            ),
            DepartmentMapping(
                category=Category.OTHER.value,
                subcategory="ENVIRONMENTAL_HAZARD",
                primary_department=Department.ENVIRONMENT_POLLUTION.value,
                responsible_unit="Environmental Protection Team",
                escalation_department="Pollution Control Board",
                baseline_priority="HIGH",
            ),
        ]

        for mapping in sub_overrides:
            self._subcategory_mappings[(mapping.category, mapping.subcategory)] = mapping

    def resolve_routing(self, category_str: str, subcategory_str: str) -> Tuple[DepartmentMapping, str]:
        """
        Determines the deterministic department mapping.
        Returns (DepartmentMapping, selection_reason).
        """
        cat_upper = category_str.upper().strip() if category_str else "OTHER"
        sub_upper = subcategory_str.upper().strip() if subcategory_str else "OTHER"

        # 1. Exact Subcategory Rule Match
        exact_key = (cat_upper, sub_upper)
        if exact_key in self._subcategory_mappings:
            return (
                self._subcategory_mappings[exact_key],
                f"Exact subcategory rule match for category '{cat_upper}' and subcategory '{sub_upper}'.",
            )

        # 2. Category Baseline Match
        if cat_upper in self._category_mappings:
            return (
                self._category_mappings[cat_upper],
                f"Category baseline rule match for category '{cat_upper}'.",
            )

        # 3. Fallback to OTHER / Civic Helpdesk
        fallback_mapping = self._category_mappings.get(
            Category.OTHER.value,
            DepartmentMapping(
                category="OTHER",
                subcategory="*",
                primary_department=Department.OTHER_GENERAL.value,
                responsible_unit="Customer Support Triage Unit",
                escalation_department="Municipal Secretary Office",
                baseline_priority="LOW",
            ),
        )
        return (
            fallback_mapping,
            f"Unknown or unmapped category '{category_str}'. Defaulted to General Civic Helpdesk.",
        )


department_registry = DepartmentRegistry()
