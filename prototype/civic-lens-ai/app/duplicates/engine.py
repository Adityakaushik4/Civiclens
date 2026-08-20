import math
import uuid
import datetime
from typing import List, Tuple, Optional
from app.schemas import (
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    DuplicateAction,
    ScoreBreakdown,
    Category,
)
from app.duplicates.store import MasterIssueRecord, DuplicateReviewRecord, master_issue_store
from app.gis.vulnerability import vulnerable_location_evaluator


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate geographic distance between two coordinates in meters using Haversine formula."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return R * c


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two dense embedding vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


class DuplicateDetectionEngine:
    """
    CivicLens Deterministic Multi-Signal Duplicate Detection Engine.
    Combines:
    - Haversine Geographic Distance (500m hard cutoff)
    - Multilingual Vector Cosine Similarity (gemini-embedding-001)
    - Categorical & Subcategory Matching
    - Exponential Time Decay
    - Signal Weight Normalization when optional signals (image) are absent
    - Subcategory Conflict Safety Capping
    """

    MAX_GEO_RADIUS_METERS = 500.0
    AUTOMATIC_MERGE_THRESHOLD = 0.82
    HUMAN_REVIEW_THRESHOLD = 0.65

    def score_pair(
        self,
        req: DuplicateCheckRequest,
        master: MasterIssueRecord,
        text_embedding: List[float]
    ) -> Tuple[float, ScoreBreakdown]:
        # 1. Geographic Distance Calculation
        dist_m = haversine_distance(req.latitude, req.longitude, master.latitude, master.longitude)

        # Hard Geo-Fence Cutoff: Disqualify if > 500m
        if dist_m > self.MAX_GEO_RADIUS_METERS:
            breakdown = ScoreBreakdown(
                geographic_distance_meters=round(dist_m, 2),
                spatial_score=0.0,
                semantic_similarity=0.0,
                category_match_score=0.0,
                temporal_score=0.0,
                total_score=0.0,
                normalized_weights_used=False
            )
            return 0.0, breakdown

        # Spatial score (1.0 at 0m, 0.0 at 500m)
        s_geo = max(0.0, 1.0 - (dist_m / self.MAX_GEO_RADIUS_METERS))

        # 2. Semantic Similarity
        s_sem = cosine_similarity(text_embedding, master.embedding) if text_embedding and master.embedding else 0.85

        # 3. Categorical Match Score
        if req.category == master.category and req.subcategory == master.subcategory:
            s_cat = 1.0
        elif req.category == master.category:
            s_cat = 0.7
        else:
            s_cat = 0.0

        # 4. Temporal Proximity (Exponential decay over 30 days)
        now = datetime.datetime.now(datetime.timezone.utc)
        created_time = master.created_at
        if created_time.tzinfo is None:
            created_time = created_time.replace(tzinfo=datetime.timezone.utc)
        delta_days = (now - created_time).total_seconds() / 86400.0
        s_time = math.exp(-max(0.0, delta_days) / 30.0)

        # 5. Signal Weight Normalization when image is missing
        if req.image_embedding and hasattr(master, "image_embedding") and master.image_embedding:
            w_geo, w_sem, w_cat, w_time, w_img = 0.35, 0.35, 0.15, 0.10, 0.05
            s_img = cosine_similarity(req.image_embedding, master.image_embedding)
            normalized_used = False
        else:
            # Re-scale active weights so sum equals 1.0
            sum_active = 0.35 + 0.35 + 0.15 + 0.10  # 0.95
            w_geo = 0.35 / sum_active
            w_sem = 0.35 / sum_active
            w_cat = 0.15 / sum_active
            w_time = 0.10 / sum_active
            w_img = 0.0
            s_img = 0.0
            normalized_used = True

        # Total Hybrid Score Formula
        total_score = w_geo * s_geo + w_sem * s_sem + w_cat * s_cat + w_time * s_time + w_img * s_img
        total_score = max(0.0, min(1.0, total_score))

        breakdown = ScoreBreakdown(
            geographic_distance_meters=round(dist_m, 2),
            spatial_score=round(s_geo, 4),
            semantic_similarity=round(s_sem, 4),
            category_match_score=round(s_cat, 4),
            temporal_score=round(s_time, 4),
            total_score=round(total_score, 4),
            normalized_weights_used=normalized_used
        )
        return total_score, breakdown

    def process_check(
        self,
        req: DuplicateCheckRequest,
        text_embedding: List[float],
        reporter_id: Optional[str] = None,
    ) -> DuplicateCheckResponse:
        candidates = master_issue_store.list_all()

        best_score = 0.0
        best_breakdown = ScoreBreakdown(
            geographic_distance_meters=0.0,
            spatial_score=0.0,
            semantic_similarity=0.0,
            category_match_score=0.0,
            temporal_score=0.0,
            total_score=0.0,
            normalized_weights_used=False
        )
        best_master: Optional[MasterIssueRecord] = None
        min_dist = float("inf")

        for master in candidates:
            dist = haversine_distance(req.latitude, req.longitude, master.latitude, master.longitude)
            if dist < min_dist:
                min_dist = dist

            score, breakdown = self.score_pair(req, master, text_embedding)
            if score > best_score:
                best_score = score
                best_breakdown = breakdown
                best_master = master

        if not best_master and min_dist < float("inf"):
            best_breakdown.geographic_distance_meters = round(min_dist, 2)

        # Check for subcategory conflict safety
        subcategory_conflict = False
        if best_master and req.category == best_master.category and req.subcategory != best_master.subcategory:
            subcategory_conflict = True

        # Determine Decision Action
        if best_master and best_score >= self.AUTOMATIC_MERGE_THRESHOLD and not subcategory_conflict:
            action = DuplicateAction.AUTOMATIC_MERGE
            # Merge complaint into master issue & recalculate running average centroid
            best_master.merge_complaint(req.latitude, req.longitude)
            return DuplicateCheckResponse(
                action=action,
                matched_master_issue_id=best_master.id,
                master_issue=best_master.to_model(),
                total_score=round(best_score, 4),
                score_breakdown=best_breakdown,
                citizen_reporter_count=best_master.citizen_reporter_count
            )

        elif best_master and (best_score >= self.HUMAN_REVIEW_THRESHOLD or subcategory_conflict):
            action = DuplicateAction.HUMAN_REVIEW_RECOMMENDED
            review_id = str(uuid.uuid4())
            complaint_id_str = req.complaint_id or str(uuid.uuid4())

            # Persistent Human Review Queue record creation
            review_rec = DuplicateReviewRecord(
                review_id=review_id,
                complaint_id=complaint_id_str,
                candidate_master_issue_id=best_master.id,
                similarity_score=round(best_score, 4),
                score_breakdown=best_breakdown,
                complaint_lat=req.latitude,
                complaint_lon=req.longitude,
                complaint_text=req.text,
                category=req.category,
                subcategory=req.subcategory,
                embedding=text_embedding
            )
            master_issue_store.add_review(review_rec)

            return DuplicateCheckResponse(
                action=action,
                matched_master_issue_id=best_master.id,
                master_issue=best_master.to_model(),
                total_score=round(best_score, 4),
                score_breakdown=best_breakdown,
                citizen_reporter_count=best_master.citizen_reporter_count,
                review_id=review_id
            )

        else:
            action = DuplicateAction.NEW_MASTER_ISSUE
            # Apply deterministic backend severity rules
            severity = req.severity
            if req.safety_risk:
                severity = max(severity, 4)
            vuln_multiplier, _ = vulnerable_location_evaluator.calculate_vulnerability_factor(req.latitude, req.longitude)
            if vuln_multiplier > 1.2:
                severity = min(5, severity + 1)
            
            # Create a new Master Issue record for this cluster
            new_master = master_issue_store.create_master_issue(
                title=req.text,
                category=req.category,
                subcategory=req.subcategory,
                latitude=req.latitude,
                longitude=req.longitude,
                description=req.description,
                severity=severity,
                embedding=text_embedding,
                reporter_id=reporter_id
            )
            return DuplicateCheckResponse(
                action=action,
                matched_master_issue_id=new_master.id,
                master_issue=new_master.to_model(),
                total_score=round(best_score, 4),
                score_breakdown=best_breakdown,
                citizen_reporter_count=new_master.citizen_reporter_count
            )
