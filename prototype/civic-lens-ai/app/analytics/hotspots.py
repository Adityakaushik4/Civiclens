import hashlib
import datetime
from typing import Dict, List, Optional
from app.analytics.schemas import CivicHotspot
from app.duplicates import master_issue_store, MasterIssueRecord
from app.gis.vulnerability import haversine_distance_meters
from app.database.connection import SessionLocal
from app.database.models import CivicHotspotModel


class HotspotStore:
    """Persistent database-backed store for Civic Hotspots."""

    def __init__(self):
        self._hotspots: Dict[str, CivicHotspot] = {}

    def save(self, hotspot: CivicHotspot) -> None:
        self._hotspots[hotspot.hotspot_id] = hotspot
        db = SessionLocal()
        try:
            cat_str = hotspot.category.value if hasattr(hotspot.category, "value") else str(hotspot.category)
            db_obj = db.query(CivicHotspotModel).filter_by(hotspot_id=hotspot.hotspot_id).first()
            if not db_obj:
                db_obj = CivicHotspotModel(
                    hotspot_id=hotspot.hotspot_id,
                    jurisdiction_id=hotspot.jurisdiction_id,
                    ward_name=hotspot.ward_name,
                    category=cat_str,
                    center_latitude=hotspot.center_latitude,
                    center_longitude=hotspot.center_longitude,
                    radius_meters=hotspot.radius_meters,
                    master_issue_count=hotspot.master_issue_count,
                    citizen_report_count=hotspot.citizen_report_count,
                    severity_score_weighted=hotspot.severity_score_weighted,
                    vulnerable_location_near=hotspot.vulnerable_location_near,
                    suppressed_publicly=hotspot.suppressed_publicly,
                    linked_master_issue_ids_json=hotspot.linked_master_issue_ids,
                )
                db.add(db_obj)
            else:
                db_obj.master_issue_count = hotspot.master_issue_count
                db_obj.citizen_report_count = hotspot.citizen_report_count
                db_obj.severity_score_weighted = hotspot.severity_score_weighted
                db_obj.linked_master_issue_ids_json = hotspot.linked_master_issue_ids
                db_obj.suppressed_publicly = hotspot.suppressed_publicly
                
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def get(self, hotspot_id: str) -> Optional[CivicHotspot]:
        return self._hotspots.get(hotspot_id)

    def list_all(self, jurisdiction_id: Optional[str] = None) -> List[CivicHotspot]:
        if jurisdiction_id:
            return [h for h in self._hotspots.values() if not h.jurisdiction_id or h.jurisdiction_id == jurisdiction_id]
        return list(self._hotspots.values())

    def clear(self) -> None:
        self._hotspots.clear()
        db = SessionLocal()
        try:
            db.query(CivicHotspotModel).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


hotspot_store = HotspotStore()


class HotspotDetectionEngine:
    """Engine detecting spatial hotspots via geodesic radius clustering and applying small-cell privacy suppression."""

    def detect_hotspots(
        self,
        jurisdiction_id: Optional[str] = None,
        radius_meters: int = 500,
    ) -> List[CivicHotspot]:
        master_records = master_issue_store.list_all()
        if not master_records:
            return []

        clusters: List[List[MasterIssueRecord]] = []
        visited = set()

        for i, rec1 in enumerate(master_records):
            if rec1.id in visited:
                continue
            cluster = [rec1]
            visited.add(rec1.id)

            for j, rec2 in enumerate(master_records):
                if rec2.id in visited:
                    continue
                dist_meters = haversine_distance_meters(rec1.latitude, rec1.longitude, rec2.latitude, rec2.longitude)
                if dist_meters <= radius_meters:
                    cluster.append(rec2)
                    visited.add(rec2.id)

            clusters.append(cluster)

        detected_hotspots: List[CivicHotspot] = []
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for cluster in clusters:
            avg_lat = sum(c.latitude for c in cluster) / len(cluster)
            avg_lon = sum(c.longitude for c in cluster) / len(cluster)

            total_reports = sum(c.citizen_reporter_count for c in cluster)
            category_counts = {}
            for c in cluster:
                c_val = c.category.value if hasattr(c.category, "value") else str(c.category)
                category_counts[c_val] = category_counts.get(c_val, 0) + 1

            dom_category = max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else "GENERAL"
            weighted_severity = sum(c.severity_score * c.citizen_reporter_count for c in cluster) / max(total_reports, 1)

            # Small-cell privacy suppression if reports < 5
            is_suppressed = total_reports < 5

            # Stable ID for reconciliation
            linked_ids_sorted = sorted([c.id for c in cluster])
            stable_hash = hashlib.md5("".join(linked_ids_sorted).encode()).hexdigest()[:8]
            stable_hs_id = f"hs_{stable_hash}"

            hotspot = CivicHotspot(
                hotspot_id=stable_hs_id,
                jurisdiction_id=jurisdiction_id,
                ward_name=cluster[0].address_description or "Municipal Ward Zone",
                category=dom_category,
                center_latitude=round(avg_lat, 5),
                center_longitude=round(avg_lon, 5),
                radius_meters=radius_meters,
                master_issue_count=len(cluster),
                citizen_report_count=total_reports,
                severity_score_weighted=round(weighted_severity, 2),
                vulnerable_location_near=False,
                suppressed_publicly=is_suppressed,
                linked_master_issue_ids=[c.id for c in cluster],
                created_at=now_str,
            )

            hotspot_store.save(hotspot)
            detected_hotspots.append(hotspot)

        return detected_hotspots


hotspot_engine = HotspotDetectionEngine()
