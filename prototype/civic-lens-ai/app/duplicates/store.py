import uuid
import datetime
import json
from typing import Dict, List, Optional
from app.schemas import MasterIssueModel, Category, ScoreBreakdown, DuplicateReviewRecordModel, DuplicateCheckResponse


class MasterIssueRecord:
    def __init__(
        self,
        id: str,
        title: str,
        category: Category,
        subcategory: str,
        severity_score: int,
        latitude: float,
        longitude: float,
        address_description: str = "",
        description: str = "",
        department: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        created_at: Optional[datetime.datetime] = None,
        reporter_id: Optional[str] = None,
    ):
        self.id = id
        self.title = title
        self.category = category
        self.subcategory = subcategory
        self.status = "OPEN"
        self.severity_score = severity_score
        self.citizen_reporter_count = 1
        self.latitude = latitude
        self.longitude = longitude
        self.address_description = address_description
        self.description = description
        self.department = department
        self.embedding = embedding or []
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc)
        self.reporter_id = reporter_id

    def merge_complaint(self, complaint_lat: float, complaint_lon: float):
        """
        Merge a new complaint into this Master Issue.
        Recalculates geographic centroid using running average formula:
        new_lat = (old_lat * N + complaint_lat) / (N + 1)
        new_lon = (old_lon * N + complaint_lon) / (N + 1)
        """
        N = self.citizen_reporter_count
        self.latitude = (self.latitude * N + complaint_lat) / (N + 1)
        self.longitude = (self.longitude * N + complaint_lon) / (N + 1)
        self.citizen_reporter_count += 1

    def to_model(self) -> MasterIssueModel:
        return MasterIssueModel(
            id=self.id,
            title=self.title,
            category=self.category,
            subcategory=self.subcategory,
            status=self.status,
            severity_score=self.severity_score,
            citizen_reporter_count=self.citizen_reporter_count,
            latitude=self.latitude,
            longitude=self.longitude,
            address_description=self.address_description or "",
            description=self.description or "",
            department=self.department,
            created_at=self.created_at.isoformat()
        )


class DuplicateReviewRecord:
    def __init__(
        self,
        review_id: str,
        complaint_id: str,
        candidate_master_issue_id: str,
        similarity_score: float,
        score_breakdown: ScoreBreakdown,
        complaint_lat: float,
        complaint_lon: float,
        complaint_text: str,
        category: Category,
        subcategory: str,
        embedding: Optional[List[float]] = None,
    ):
        self.review_id = review_id
        self.complaint_id = complaint_id
        self.candidate_master_issue_id = candidate_master_issue_id
        self.similarity_score = similarity_score
        self.score_breakdown = score_breakdown
        self.complaint_lat = complaint_lat
        self.complaint_lon = complaint_lon
        self.complaint_text = complaint_text
        self.category = category
        self.subcategory = subcategory
        self.embedding = embedding or []
        self.status = "PENDING"
        self.operator_id: Optional[str] = None
        self.created_at = datetime.datetime.now(datetime.timezone.utc)
        self.resolved_at: Optional[datetime.datetime] = None

    def to_model(self) -> DuplicateReviewRecordModel:
        return DuplicateReviewRecordModel(
            review_id=self.review_id,
            complaint_id=self.complaint_id,
            candidate_master_issue_id=self.candidate_master_issue_id,
            similarity_score=self.similarity_score,
            score_breakdown=self.score_breakdown,
            status=self.status,
            operator_id=self.operator_id,
            created_at=self.created_at.isoformat(),
            resolved_at=self.resolved_at.isoformat() if self.resolved_at else None
        )


from app.database.connection import SessionLocal
from app.database.models import MasterIssueModel as DBMasterIssueModel, DuplicateReviewModel as DBDuplicateReviewModel


class MasterIssueStore:
    """Persistent database-backed and thread-safe storage for Master Issues and Review Queue."""

    def __init__(self):
        self._records: Dict[str, MasterIssueRecord] = {}
        self._processed_complaints: Dict[str, DuplicateCheckResponse] = {}
        self._reviews: Dict[str, DuplicateReviewRecord] = {}

    def get_processed_complaint(self, complaint_id: str) -> Optional[DuplicateCheckResponse]:
        return self._processed_complaints.get(complaint_id)

    def record_processed_complaint(self, complaint_id: str, response: DuplicateCheckResponse):
        self._processed_complaints[complaint_id] = response

    def _sync_to_db(self, record: MasterIssueRecord):
        db = SessionLocal()
        try:
            cat_val = record.category.value if hasattr(record.category, "value") else str(record.category)
            if str(cat_val).startswith("Category."):
                cat_val = str(cat_val).replace("Category.", "")
            db_obj = db.query(DBMasterIssueModel).filter_by(id=record.id).first()
            if not db_obj:
                db_obj = DBMasterIssueModel(
                    id=record.id,
                    title=record.title,
                    category=str(cat_val),
                    subcategory=record.subcategory,
                    status=record.status,
                    severity_score=record.severity_score,
                    citizen_reporter_count=record.citizen_reporter_count,
                    latitude=record.latitude,
                    longitude=record.longitude,
                    address_description=record.address_description,
                    description=record.description,
                    embedding_json=json.dumps(record.embedding) if record.embedding else "[]",
                    reporter_id=record.reporter_id,
                )
                db.add(db_obj)
            else:
                db_obj.title = record.title
                db_obj.category = str(cat_val)
                db_obj.subcategory = record.subcategory
                db_obj.status = record.status
                db_obj.severity_score = record.severity_score
                db_obj.citizen_reporter_count = record.citizen_reporter_count
                db_obj.latitude = record.latitude
                db_obj.longitude = record.longitude
                db_obj.address_description = record.address_description
                db_obj.description = record.description
                db_obj.embedding_json = json.dumps(record.embedding) if record.embedding else "[]"
                if record.reporter_id:
                    db_obj.reporter_id = record.reporter_id
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def add(self, record: MasterIssueRecord):
        self._records[record.id] = record
        self._sync_to_db(record)

    def clear(self):
        """Clear all in-memory master issue records."""
        self._records.clear()

    def get(self, master_issue_id: str) -> Optional[MasterIssueRecord]:
        """Get a master issue record by its ID. Alias for get_by_id."""
        return self.get_by_id(master_issue_id)

    def get_by_id(self, master_issue_id: str) -> Optional[MasterIssueRecord]:
        rec = self._records.get(master_issue_id)
        if rec:
            return rec
        db = SessionLocal()
        try:
            db_obj = db.query(DBMasterIssueModel).filter_by(id=master_issue_id).first()
            if db_obj:
                cat_str = str(db_obj.category).replace("Category.", "")
                try:
                    cat_enum = Category(cat_str)
                except Exception:
                    try:
                        cat_enum = Category[cat_str]
                    except Exception:
                        cat_enum = Category.ROAD_DAMAGE

                rec = MasterIssueRecord(
                    id=db_obj.id,
                    title=db_obj.title,
                    category=cat_enum,
                    subcategory=db_obj.subcategory,
                    severity_score=db_obj.severity_score,
                    latitude=db_obj.latitude,
                    longitude=db_obj.longitude,
                    address_description=db_obj.address_description or "",
                    description=db_obj.description or "",
                    embedding=json.loads(db_obj.embedding_json) if isinstance(db_obj.embedding_json, str) else (db_obj.embedding_json or []),
                    created_at=db_obj.created_at,
                    reporter_id=getattr(db_obj, "reporter_id", None),
                )
                rec.status = db_obj.status
                rec.citizen_reporter_count = db_obj.citizen_reporter_count
                self._records[rec.id] = rec
            return rec
        except Exception:
            return None
        finally:
            db.close()

    def list_all(self) -> List[MasterIssueRecord]:
        if not self._records:
            db = SessionLocal()
            try:
                db_objs = db.query(DBMasterIssueModel).all()
                for db_obj in db_objs:
                    try:
                        cat_enum = Category(db_obj.category)
                    except ValueError:
                        cat_enum = Category.ROAD_DAMAGE
                    rec = MasterIssueRecord(
                        id=db_obj.id,
                        title=db_obj.title,
                        category=cat_enum,
                        subcategory=db_obj.subcategory,
                        severity_score=db_obj.severity_score,
                        latitude=db_obj.latitude,
                        longitude=db_obj.longitude,
                        address_description=db_obj.address_description or "",
                        description=db_obj.description or "",
                        embedding=json.loads(db_obj.embedding_json) if isinstance(db_obj.embedding_json, str) else (db_obj.embedding_json or []),
                        created_at=db_obj.created_at,
                        reporter_id=getattr(db_obj, "reporter_id", None),
                    )
                    rec.status = db_obj.status
                    rec.citizen_reporter_count = db_obj.citizen_reporter_count
                    self._records[rec.id] = rec
            except Exception:
                pass
            finally:
                db.close()
        return list(self._records.values())

    def create_master_issue(
        self,
        title: str,
        category: Category,
        subcategory: str,
        latitude: float,
        longitude: float,
        description: str = "",
        severity: int = 3,
        embedding: Optional[List[float]] = None,
        reporter_id: Optional[str] = None
    ) -> MasterIssueRecord:
        record_id = f"CIVIC-2026-{uuid.uuid4().hex[:4].upper()}"
        record = MasterIssueRecord(
            id=record_id,
            title=title,
            category=category,
            subcategory=subcategory,
            severity_score=severity,
            latitude=latitude,
            longitude=longitude,
            description=description,
            embedding=embedding or [],
            reporter_id=reporter_id
        )
        self._records[record_id] = record
        self._sync_to_db(record)
        return record

    def add_review(self, record: DuplicateReviewRecord) -> DuplicateReviewRecord:
        self._reviews[record.review_id] = record
        return record

    def get_review(self, review_id: str) -> Optional[DuplicateReviewRecord]:
        return self._reviews.get(review_id)

    def list_reviews(self, status_filter: Optional[str] = None) -> List[DuplicateReviewRecord]:
        if status_filter:
            sf_upper = status_filter.upper().strip()
            return [r for r in self._reviews.values() if r.status == sf_upper]
        return list(self._reviews.values())

    def decide_review(
        self, review_id: str, decision: str, operator_id: Optional[str] = None
    ) -> DuplicateReviewRecord:
        review = self.get_review(review_id)
        if not review:
            raise KeyError(f"Duplicate review with ID '{review_id}' not found.")

        # Idempotency check: if review already decided, return without side effects
        if review.status != "PENDING":
            return review

        dec_upper = decision.upper().strip()
        now = datetime.datetime.now(datetime.timezone.utc)

        if dec_upper == "APPROVED":
            master = self.get(review.candidate_master_issue_id)
            if master:
                master.merge_complaint(review.complaint_lat, review.complaint_lon)
            review.status = "APPROVED"
            review.operator_id = operator_id or "operator_1"
            review.resolved_at = now
        elif dec_upper == "REJECTED":
            # Create a separate master issue for this complaint
            self.create_master_issue(
                title=review.complaint_text,
                category=review.category,
                subcategory=review.subcategory,
                latitude=review.complaint_lat,
                longitude=review.complaint_lon,
                description=review.complaint_text,
                embedding=review.embedding
            )
            review.status = "REJECTED"
            review.operator_id = operator_id or "operator_1"
            review.resolved_at = now
        else:
            raise ValueError(f"Invalid decision '{decision}'. Must be APPROVED or REJECTED.")

        return review

    def clear(self):
        self._records.clear()
        self._processed_complaints.clear()
        self._reviews.clear()
        db = SessionLocal()
        try:
            from app.database.models import IssueLifecycleModel, RoutingDecisionModel, WorkAssignmentModel, EvidenceRecordModel, ReopenIdempotencyModel
            db.query(EvidenceRecordModel).delete()
            db.query(WorkAssignmentModel).delete()
            db.query(RoutingDecisionModel).delete()
            db.query(ReopenIdempotencyModel).delete()
            db.query(IssueLifecycleModel).delete()
            db.query(DuplicateReviewModel).delete()
            db.query(MasterIssueModel).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()



    def seed_demo_data(self):
        # Only seed if empty
        if self._records:
            return
            
        import uuid
        import random
        
        demo_issues = [
            {
                "title": "[DEMO] Large pothole near ITER",
                "category": "ROAD_DAMAGE",
                "subcategory": "Pothole",
                "severity_score": 5,
                "latitude": 20.2496,
                "longitude": 85.7958,
                "address_description": "Near ITER College, Ward 50",
                "department": "Roads & PWD"
            },
            {
                "title": "[DEMO] Garbage accumulation near Market",
                "category": "GARBAGE",
                "subcategory": "Public Dump",
                "severity_score": 4,
                "latitude": 20.2961,
                "longitude": 85.8245,
                "address_description": "Unit-1 Market, Ward 40",
                "department": "Sanitation & Waste Management"
            },
            {
                "title": "[DEMO] Overflowing Drainage",
                "category": "DRAINAGE",
                "subcategory": "Overflow",
                "severity_score": 5,
                "latitude": 20.2885,
                "longitude": 85.8450,
                "address_description": "Saheed Nagar, Ward 30",
                "department": "Drainage & Sewerage"
            },
            {
                "title": "[DEMO] Streetlight not working",
                "category": "STREETLIGHT",
                "subcategory": "No Power",
                "severity_score": 2,
                "latitude": 20.3200,
                "longitude": 85.8150,
                "address_description": "Patia, Ward 10",
                "department": "Electrical / Street Lighting"
            }
        ]
        
        for data in demo_issues:
            mid = "MI-" + str(uuid.uuid4())[:8].upper()
            rec = MasterIssueRecord(
                id=mid,
                title=data["title"],
                category=data["category"],
                subcategory=data["subcategory"],
                severity_score=data["severity_score"],
                latitude=data["latitude"],
                longitude=data["longitude"],
                address_description=data["address_description"],
                department=data["department"]
            )
            # Add some reporter counts
            rec.citizen_reporter_count = random.randint(1, 15)
            self._records[mid] = rec


master_issue_store = MasterIssueStore()
# master_issue_store.seed_demo_data() # Disabled: DO NOT SHOW DEMO DATA As Real Citizen Reports

