import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag.schemas import DocumentChunk, DocumentVersion, AuthorityStatus, AccessLevel, ChunkEmbedding, DocumentType
from app.rag.store import rag_vector_store
from app.rag.ingestion import rag_ingestion_engine
from app.database.connection import SessionLocal
from app.database.models import RAGDocumentModel
from app.rag.store import CivicDocument

import datetime
import uuid

def seed():
    db = SessionLocal()
    count = db.query(RAGDocumentModel).count()
    if count > 0:
        print("Knowledge base already seeded. Exiting.")
        return

    print("Seeding Knowledge Base with realistic documents...")

    docs_data = [
        {
            "title": "Municipal Roads & PWD Standard Operating Procedure 2026",
            "issuing_authority": "Public Works Department",
            "document_type": DocumentType.POLICY,
            "text": """
# Municipal Roads & PWD SOP 2026

## 1. Pothole Repair Guidelines
All potholes exceeding 5cm in depth on arterial roads must be filled and compacted within 48 hours of reporting. 
The material used must be cold-mix asphalt during monsoon season and hot-mix during dry seasons.

## 2. Road Resurfacing Policy
Complete road resurfacing is warranted if more than 30% of a 100-meter stretch is damaged. 
The minimum budget allocation for a 1 km stretch of arterial road resurfacing is estimated at $120,000. 
Ward councilors must approve resurfacing projects exceeding $50,000.

## 3. Waterlogging on Roads
Roads prone to waterlogging must be inspected before the monsoon season (May-June). 
Drainage clearing is mandatory along these stretches. If waterlogging persists for more than 12 hours after rainfall, 
emergency pumping must be deployed.
            """
        },
        {
            "title": "Sanitation & Waste Management Guidelines",
            "issuing_authority": "Department of Sanitation",
            "document_type": DocumentType.OPERATIONAL_GUIDELINE,
            "text": """
# Sanitation & Waste Management Guidelines

## 1. Garbage Collection Frequencies
Residential areas must have daily door-to-door garbage collection. 
Commercial zones require twice-a-day collection (morning and evening).

## 2. Public Dustbins
Overflowing public dustbins are a critical health hazard. They must be cleared within 12 hours of an citizen complaint.
Any damaged dustbins must be replaced within 72 hours. Standard replacement cost per bin is $150.

## 3. Illegal Dumping
Illegal dumping of construction or medical waste carries a fine of up to $5,000. 
Citizens reporting illegal dumping with photographic evidence will be prioritized, and cleanup must be initiated within 24 hours.
            """
        },
        {
            "title": "Sewerage & Drainage Maintenance Policy",
            "issuing_authority": "Water & Sewerage Board",
            "document_type": DocumentType.POLICY,
            "text": """
# Sewerage & Drainage Maintenance Policy

## 1. Open Manholes
An open manhole is a severe safety risk (Severity: CRITICAL). 
Immediate barricading must be done within 2 hours of a report. 
Permanent cover replacement must happen within 24 hours.

## 2. Clogged Drains
Minor localized clogging should be cleared within 72 hours. 
Major sewerage blockages causing street overflow require a high-capacity vacuum truck. 
The standard operating cost for deploying a vacuum truck is $400 per incident.

## 3. Upgrading Drainage Infrastructure
Proposals for new underground drainage lines must undergo a feasibility study if the requested budget exceeds $200,000. 
Priority is given to wards with historical reporting of annual monsoon flooding.
            """
        }
    ]

    for data in docs_data:
        doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
        doc = CivicDocument(
            document_id=doc_id,
            title=data["title"],
            issuing_authority=data["issuing_authority"],
            jurisdiction_id="*",
            document_type=data["document_type"],
            authority_status=AuthorityStatus.AUTHORITATIVE,
            access_level=AccessLevel.PUBLIC,
            current_version_id="v1.0",
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        rag_vector_store.save_document(doc)

        version = DocumentVersion(
            version_id=f"VER-{uuid.uuid4().hex[:8].upper()}",
            document_id=doc_id,
            version_number="1.0",
            file_name=f"{data['title'].replace(' ', '_')}.txt",
            checksum="seeded_checksum",
            source_reference=data["title"],
            effective_from=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            file_key=f"rag_files/{doc_id}.txt",
            mime_type="text/plain",
            ingested_by="admin_seed",
            ingestion_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        rag_vector_store.save_version(version)

        # Naive chunking for seeding purposes
        chunk = DocumentChunk(
            chunk_id=f"CHK-{uuid.uuid4().hex[:8].upper()}",
            document_id=doc_id,
            version_id=version.version_id,
            chunk_index=0,
            section_title="Main Content",
            page_number=1,
            content_text=data["text"],
            token_count=len(data["text"].split()),
            jurisdiction_id="*",
            authority_status=AuthorityStatus.AUTHORITATIVE,
            access_level=AccessLevel.PUBLIC,
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        rag_vector_store.save_chunks([chunk])

        # Get embeddings from the embedding provider
        from app.embeddings import get_embedding_provider
        provider = get_embedding_provider()
        try:
            vec = provider.get_embedding(data["text"])
        except Exception:
            vec = [0.0] * 3072

        emb = ChunkEmbedding(
            embedding_id=f"emb_{uuid.uuid4().hex[:8]}",
            chunk_id=chunk.chunk_id,
            dimensions=len(vec),
            vector=vec
        )
        rag_vector_store.save_embeddings([emb])
        print(f"Indexed: {data['title']}")

    print("Knowledge Base seeding complete.")
    db.close()

if __name__ == "__main__":
    seed()
