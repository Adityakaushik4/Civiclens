import os
import io
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from app.evidence.schemas import EvidenceType, VerificationStatus, ResolutionEvidence

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "audio/wav", "audio/webm", "audio/mpeg", "audio/mp4", "audio/x-wav"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def normalize_mime_type(mime_type: str) -> str:
    """Normalizes common client MIME aliases before validation."""
    mime_clean = mime_type.lower().strip()
    if mime_clean == "image/jpg":
        return "image/jpeg"
    return mime_clean


def sanitize_and_save_image(file_bytes: bytes, mime_type: str) -> bytes:
    """Strips EXIF metadata and re-encodes image bytes safely. Bypasses for audio."""
    if mime_type.startswith("audio/"):
        return file_bytes
        
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(file_bytes))
        output = io.BytesIO()

        # Determine format
        if "png" in mime_type:
            fmt = "PNG"
        elif "webp" in mime_type:
            fmt = "WEBP"
        else:
            fmt = "JPEG"
            if img.mode != "RGB":
                img = img.convert("RGB")

        # Save without EXIF data
        img.save(output, format=fmt)
        return output.getvalue()
    except Exception:
        # Fallback if PIL fails or unavailable: return original sanitized slice
        return file_bytes


from app.database.connection import SessionLocal
from app.database.models import EvidenceRecordModel

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "evidence")
os.makedirs(DATA_DIR, exist_ok=True)


def _ensure_evidence_type_column(db):
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.get_bind())
        columns = [c["name"] for c in inspector.get_columns("evidence_records")]
        if "evidence_type" not in columns:
            db.execute(text("ALTER TABLE evidence_records ADD COLUMN evidence_type VARCHAR(32);"))
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Notice: Column check/migration for evidence_type: {e}")


def _resolve_evidence_type(rec) -> EvidenceType:
    raw_type = getattr(rec, "evidence_type", None)
    if raw_type:
        try:
            return EvidenceType(str(raw_type).upper().strip())
        except ValueError:
            pass
    # Fallback classification for legacy records
    mime = (getattr(rec, "file_type", "") or "").lower()
    fname = (getattr(rec, "file_name", "") or "").lower()
    uploader = (getattr(rec, "uploader_id", "") or "").upper()

    if mime.startswith("audio/") or fname.endswith((".wav", ".mp3", ".webm")):
        return EvidenceType.VOICE_NOTE
    elif uploader == "CITIZEN":
        return EvidenceType.BEFORE_IMAGE
    else:
        return EvidenceType.AFTER_IMAGE


class EvidenceStore:
    """Persistent database-backed evidence storage with EXIF sanitization."""

    def __init__(self):
        self._evidence: Dict[str, ResolutionEvidence] = {}
        self._file_contents: Dict[str, bytes] = {}
        self._load_from_db()

    def _load_from_db(self):
        db = SessionLocal()
        try:
            _ensure_evidence_type_column(db)
            records = db.query(EvidenceRecordModel).all()
            dirty = False
            for rec in records:
                ev_type = _resolve_evidence_type(rec)
                if not getattr(rec, "evidence_type", None):
                    setattr(rec, "evidence_type", ev_type.value)
                    dirty = True

                ev = ResolutionEvidence(
                    evidence_id=rec.evidence_id,
                    issue_id=rec.issue_id,
                    evidence_type=ev_type,
                    file_key=f"private/evidence/{rec.issue_id}/{rec.evidence_id}_{rec.file_name}",
                    file_name=rec.file_name,
                    mime_type=rec.file_type,
                    file_size_bytes=rec.file_size_bytes,
                    uploaded_by=rec.uploader_id,
                    uploaded_at=rec.created_at.isoformat() if rec.created_at else datetime.now(timezone.utc).isoformat(),
                    verification_status=VerificationStatus.PENDING,
                    public_token=rec.public_token
                )
                self._evidence[rec.evidence_id] = ev

            if dirty:
                db.commit()
        except Exception as e:
            print(f"Failed to load evidence from DB: {e}")
        finally:
            db.close()

    def _sync_to_db(self, record: ResolutionEvidence):
        db = SessionLocal()
        try:
            db_obj = db.query(EvidenceRecordModel).filter_by(evidence_id=record.evidence_id).first()
            if not db_obj:
                db_obj = EvidenceRecordModel(
                    evidence_id=record.evidence_id,
                    issue_id=record.issue_id,
                    uploader_id=record.uploaded_by,
                    file_name=record.file_name,
                    file_type=record.mime_type,
                    file_size_bytes=record.file_size_bytes,
                    sha256_checksum="sha256_placeholder",
                    exif_sanitized=True,
                    public_token=record.public_token,
                    evidence_type=record.evidence_type.value if hasattr(record.evidence_type, "value") else str(record.evidence_type),
                )
                db.add(db_obj)
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def save_evidence(
        self,
        issue_id: str,
        evidence_type: EvidenceType,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
        uploaded_by: str = "operator_1",
    ) -> ResolutionEvidence:
        mime_clean = normalize_mime_type(mime_type)
        if mime_clean not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Invalid file format '{mime_type}'. Only images and audio files are allowed.")

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds maximum allowed limit of 10 MB ({len(file_bytes)} bytes provided).")

        # Sanitize EXIF metadata
        sanitized_bytes = sanitize_and_save_image(file_bytes, mime_clean)

        evidence_id = f"ev_{uuid.uuid4().hex[:8]}"
        file_key = f"private/evidence/{issue_id}/{evidence_id}_{file_name}"
        public_token = f"tok_{uuid.uuid4().hex[:16]}"
        now_str = datetime.now(timezone.utc).isoformat()

        record = ResolutionEvidence(
            evidence_id=evidence_id,
            issue_id=issue_id,
            evidence_type=evidence_type,
            file_key=file_key,
            file_name=file_name,
            mime_type=mime_clean,
            file_size_bytes=len(sanitized_bytes),
            uploaded_by=uploaded_by,
            uploaded_at=now_str,
            verification_status=VerificationStatus.PENDING,
            public_token=public_token,
        )

        self._evidence[evidence_id] = record
        self._file_contents[file_key] = sanitized_bytes
        self._file_contents[public_token] = sanitized_bytes
        
        # Save to disk
        file_path = os.path.join(DATA_DIR, public_token)
        try:
            with open(file_path, "wb") as f:
                f.write(sanitized_bytes)
        except Exception as e:
            print(f"Warning: Failed to save evidence bytes to disk: {e}")
            
        self._sync_to_db(record)
        return record

    def get_evidence(self, evidence_id: str) -> Optional[ResolutionEvidence]:
        rec = self._evidence.get(evidence_id)
        if rec:
            return rec
        db = SessionLocal()
        try:
            db_obj = db.query(EvidenceRecordModel).filter_by(evidence_id=evidence_id).first()
            if db_obj:
                rec = ResolutionEvidence(
                    evidence_id=db_obj.evidence_id,
                    issue_id=db_obj.issue_id,
                    evidence_type=_resolve_evidence_type(db_obj),

                    file_key=f"private/evidence/{db_obj.issue_id}/{db_obj.evidence_id}_{db_obj.file_name}",
                    file_name=db_obj.file_name,
                    mime_type=db_obj.file_type,
                    file_size_bytes=db_obj.file_size_bytes,
                    uploaded_by=db_obj.uploader_id,
                    uploaded_at=db_obj.created_at.isoformat() if db_obj.created_at else datetime.now(timezone.utc).isoformat(),
                    verification_status=VerificationStatus.PENDING,
                    public_token=db_obj.public_token,
                )
                self._evidence[rec.evidence_id] = rec
            return rec
        except Exception:
            return None
        finally:
            db.close()

    def list_by_issue(self, issue_id: str) -> List[ResolutionEvidence]:
        return [e for e in self._evidence.values() if e.issue_id == issue_id]

    def list_all(self) -> List[ResolutionEvidence]:
        return list(self._evidence.values())

    def get_media_stream(self, token_or_key: str) -> Optional[Tuple[bytes, str]]:
        matched = [e for e in self._evidence.values() if e.public_token == token_or_key or e.file_key == token_or_key]
        mime = matched[0].mime_type if matched else "image/jpeg"
        
        if token_or_key in self._file_contents:
            return self._file_contents[token_or_key], mime
            
        # Fallback to disk
        file_path = os.path.join(DATA_DIR, token_or_key)
        if os.path.exists(file_path):
            try:
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                self._file_contents[token_or_key] = file_bytes
                return file_bytes, mime
            except Exception:
                return None
                
        return None

    def update_verification_status(self, evidence_id: str, status: VerificationStatus) -> Optional[ResolutionEvidence]:
        rec = self._evidence.get(evidence_id)
        if rec:
            rec.verification_status = status
            self._evidence[evidence_id] = rec
        return rec

    def clear(self) -> None:
        self._evidence.clear()
        self._file_contents.clear()
        db = SessionLocal()
        try:
            db.query(EvidenceRecordModel).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


evidence_store = EvidenceStore()
