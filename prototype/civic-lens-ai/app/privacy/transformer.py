import math
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from app.escalation.state_machine import escalation_store, IssueStatus
from app.routing.engine import routing_store
from app.evidence.storage import evidence_store
from app.duplicates import master_issue_store
from app.gis.local_index import bhubaneswar_location_index


class PublicTimelineEntry(BaseModel):
    timestamp: str
    status: str
    actor_role: str = Field(..., description="Anonymized role, e.g., 'Field Crew Lead', 'Supervisor', 'Citizen'")
    summary: str


class PublicIssueView(BaseModel):
    public_id: str = Field(..., description="Anonymized public issue tracking ID (e.g. CIVIC-2026-8F9B)")
    issue_id: str = Field(..., description="Internal reference ID")
    category: str
    subcategory: str
    fuzzed_latitude: float = Field(..., description="Coordinates fuzzed to 3 decimal places (~100m grid)")
    fuzzed_longitude: float = Field(..., description="Coordinates fuzzed to 3 decimal places (~100m grid)")
    public_location_description: str
    status: str
    priority_level: str
    department_name: str
    citizen_report_count: int = 1
    public_evidence_urls: List[str] = Field(default_factory=list)
    public_timeline: List[PublicTimelineEntry] = Field(default_factory=list)
    updated_at: str


class PublicIssueStore:
    """In-memory store for Privacy-Preserving Public Issue Views."""

    def __init__(self):
        self._public_views: Dict[str, PublicIssueView] = {}
        self._id_mapping: Dict[str, str] = {}  # anonymized_id -> issue_id

    def save(self, view: PublicIssueView) -> None:
        self._public_views[view.public_id] = view
        self._id_mapping[view.issue_id] = view.public_id

    def get_by_public_id(self, public_id: str) -> Optional[PublicIssueView]:
        return self._public_views.get(public_id.upper().strip())

    def get_by_issue_id(self, issue_id: str) -> Optional[PublicIssueView]:
        pub_id = self._id_mapping.get(issue_id)
        if pub_id:
            return self._public_views.get(pub_id)
        return None

    def clear(self) -> None:
        self._public_views.clear()
        self._id_mapping.clear()


public_issue_store = PublicIssueStore()


class PrivacyTransformer:
    """Transforms internal complaint/master issue records into privacy-preserving public views."""

    def fuzz_coordinate(self, coord: float) -> float:
        """Fuzzes latitude/longitude to 3 decimal places (~100m grid accuracy)."""
        return round(coord, 3)

    def mask_actor(self, raw_actor: str) -> str:
        """Anonymizes internal employee IDs or citizen names into public roles."""
        if not raw_actor or raw_actor.startswith("system"):
            return "System Router"
        if "verifier" in raw_actor.lower() or "supervisor" in raw_actor.lower():
            return "Department Supervisor"
        if "operator" in raw_actor.lower() or "crew" in raw_actor.lower():
            return "Field Crew Lead"
        if "citizen" in raw_actor.lower():
            return "Citizen Reporter"
        return "Municipal Representative"

    def generate_public_view(
        self, issue_id: str, base_lat: float = 12.9716, base_lon: float = 77.5946
    ) -> PublicIssueView:
        lifecycle = escalation_store.get(issue_id)
        routing_dec = routing_store.get(issue_id)
        master_issue = master_issue_store.get(issue_id)


        # Generate or retrieve anonymized public ID
        existing = public_issue_store.get_by_issue_id(issue_id)
        if existing:
            pub_id = existing.public_id
        else:
            short_code = issue_id.split("_")[-1][:4].upper() if "_" in issue_id else uuid.uuid4().hex[:4].upper()
            pub_id = f"CIVIC-2026-{short_code}"

        # Resolve Lat/Lon
        lat = master_issue.latitude if master_issue else base_lat
        lon = master_issue.longitude if master_issue else base_lon
        report_count = master_issue.citizen_reporter_count if master_issue else 1

        fuzzed_lat = self.fuzz_coordinate(lat)
        fuzzed_lon = self.fuzz_coordinate(lon)


        cat_str = routing_dec.category if routing_dec else (master_issue.category if master_issue else "OTHER")
        sub_str = routing_dec.subcategory if routing_dec else (master_issue.subcategory if master_issue else "OTHER")
        status_enum = lifecycle.current_status.value if lifecycle else "Pending Routing"
        prio_str = routing_dec.priority_level.value if routing_dec else "Pending Assessment"
        dept_str = routing_dec.primary_department if routing_dec else "Not yet assigned"

        # Evidence URLs
        ev_list = evidence_store.list_by_issue(issue_id)
        public_urls = [
            f"/api/v1/public/evidence/{pub_id}/media/{ev.public_token}"
            for ev in ev_list
        ]

        # Anonymized Timeline
        timeline_entries: List[PublicTimelineEntry] = []
        if lifecycle and lifecycle.status_history:
            for hist in lifecycle.status_history:
                actor_role = self.mask_actor(hist.changed_by)
                timeline_entries.append(
                    PublicTimelineEntry(
                        timestamp=hist.changed_at,
                        status=hist.to_status.value,
                        actor_role=actor_role,
                        summary=f"Status updated to '{hist.to_status.value}'",
                    )
                )

        # Reverse resolve coordinates to nearest canonical location in local registry
        resolved_loc = bhubaneswar_location_index.reverse_resolve_coordinates(lat, lon)
        if resolved_loc and resolved_loc.get("canonical_name"):
            public_loc_desc = resolved_loc["canonical_name"]
        else:
            public_loc_desc = f"Municipal Zone Area ({fuzzed_lat}, {fuzzed_lon})"

        view = PublicIssueView(
            public_id=pub_id,
            issue_id=issue_id,
            category=cat_str,
            subcategory=sub_str,
            fuzzed_latitude=fuzzed_lat,
            fuzzed_longitude=fuzzed_lon,
            public_location_description=public_loc_desc,
            status=status_enum,
            priority_level=prio_str,
            department_name=dept_str,
            citizen_report_count=report_count,
            public_evidence_urls=public_urls,
            public_timeline=timeline_entries,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        public_issue_store.save(view)
        return view


privacy_transformer = PrivacyTransformer()
