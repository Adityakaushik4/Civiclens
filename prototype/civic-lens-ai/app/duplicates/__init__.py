"""Duplicate Detection Engine module."""
from app.duplicates.engine import DuplicateDetectionEngine, haversine_distance, cosine_similarity
from app.duplicates.store import master_issue_store, MasterIssueRecord

__all__ = ["DuplicateDetectionEngine", "haversine_distance", "cosine_similarity", "master_issue_store", "MasterIssueRecord"]
