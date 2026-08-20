import datetime
from typing import Dict, List, Optional, Tuple
from app.rag.schemas import (
    AuthorityStatus,
    AccessLevel,
    DocumentType,
    CivicDocument,
    DocumentVersion,
    DocumentChunk,
    ChunkEmbedding,
)



class RAGVectorStore:
    """In-memory thread-safe vector and metadata store for Civic RAG documents and 3072-dim embeddings."""

    def __init__(self):
        self._documents: Dict[str, CivicDocument] = {}
        self._versions: Dict[str, DocumentVersion] = {}
        self._chunks: Dict[str, DocumentChunk] = {}
        self._embeddings: Dict[str, ChunkEmbedding] = {}

    def save_document(self, doc: CivicDocument) -> CivicDocument:
        self._documents[doc.document_id] = doc
        return doc

    def get_document(self, doc_id: str) -> Optional[CivicDocument]:
        return self._documents.get(doc_id)

    def list_documents(self) -> List[CivicDocument]:
        return list(self._documents.values())

    def deactivate_document(self, doc_id: str) -> CivicDocument:
        doc = self._documents.get(doc_id)
        if not doc:
            raise KeyError(f"Document '{doc_id}' not found.")
        doc.authority_status = AuthorityStatus.INACTIVE
        doc.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._documents[doc_id] = doc

        # Deactivate linked versions & chunks
        for ver in self._versions.values():
            if ver.document_id == doc_id:
                ver.active = False
        for chk in self._chunks.values():
            if chk.document_id == doc_id:
                chk.authority_status = AuthorityStatus.INACTIVE

        return doc

    def save_version(self, version: DocumentVersion) -> DocumentVersion:
        self._versions[version.version_id] = version

        # Update document current version pointer
        doc = self._documents.get(version.document_id)
        if doc:
            doc.current_version_id = version.version_id
            doc.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self._documents[doc.document_id] = doc

        return version

    def get_version(self, version_id: str) -> Optional[DocumentVersion]:
        return self._versions.get(version_id)

    def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

    def save_embeddings(self, embeddings: List[ChunkEmbedding]) -> None:
        for emb in embeddings:
            self._embeddings[emb.chunk_id] = emb

    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        return self._chunks.get(chunk_id)

    def get_embedding(self, chunk_id: str) -> Optional[ChunkEmbedding]:
        return self._embeddings.get(chunk_id)

    def get_filtered_chunks(
        self,
        jurisdiction_id: Optional[str] = None,
        user_access_level: AccessLevel = AccessLevel.PUBLIC,
    ) -> List[Tuple[DocumentChunk, List[float]]]:
        """
        Retrieves active chunks with vectors that satisfy pre-retrieval metadata filtering:
        1. authority_status != INACTIVE
        2. jurisdiction_id matches requested jurisdiction OR is global (None or "*")
        3. access_level <= user_access_level (RBAC check)
        """
        role_ranks = {
            AccessLevel.PUBLIC: 1,
            AccessLevel.OPERATOR: 2,
            AccessLevel.SUPERVISOR: 3,
            AccessLevel.ADMIN: 4,
        }
        max_rank = role_ranks.get(user_access_level, 1)

        results: List[Tuple[DocumentChunk, List[float]]] = []

        for chunk in self._chunks.values():
            # Exclude inactive docs/chunks
            if chunk.authority_status == AuthorityStatus.INACTIVE:
                continue

            # RBAC check
            chunk_rank = role_ranks.get(chunk.access_level, 1)
            if chunk_rank > max_rank:
                continue

            # Jurisdiction isolation check
            if jurisdiction_id:
                if chunk.jurisdiction_id and chunk.jurisdiction_id != "*" and chunk.jurisdiction_id != jurisdiction_id:
                    continue

            # Fetch vector embedding
            emb = self._embeddings.get(chunk.chunk_id)
            if emb and emb.vector:
                results.append((chunk, emb.vector))

        return results

from app.database.connection import SessionLocal
from app.database.models import RAGDocumentModel, RAGDocumentVersionModel, RAGChunkModel, RAGEmbeddingModel


class RAGVectorStore:
    """Persistent database-backed store for RAG documents, versions, chunks, and 3072-dim embeddings."""

    def __init__(self):
        self._documents: Dict[str, CivicDocument] = {}
        self._versions: Dict[str, DocumentVersion] = {}
        self._chunks: Dict[str, DocumentChunk] = {}
        self._embeddings: Dict[str, ChunkEmbedding] = {}

    def save_document(self, doc: CivicDocument) -> CivicDocument:
        self._documents[doc.document_id] = doc
        db = SessionLocal()
        try:
            doc_type_str = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type)
            auth_str = doc.authority_status.value if hasattr(doc.authority_status, "value") else str(doc.authority_status)
            access_str = doc.access_level.value if hasattr(doc.access_level, "value") else str(doc.access_level)
            is_act = auth_str != "INACTIVE"

            db_obj = db.query(RAGDocumentModel).filter_by(document_id=doc.document_id).first()
            if not db_obj:
                db_obj = RAGDocumentModel(
                    document_id=doc.document_id,
                    title=doc.title,
                    issuing_authority=doc.issuing_authority,
                    jurisdiction_id=doc.jurisdiction_id,
                    document_type=doc_type_str,
                    authority_status=auth_str,
                    access_level=access_str,
                    source_reference=getattr(doc, "source_reference", None),
                    source_title=getattr(doc, "source_title", None),

                    current_version_id=doc.current_version_id or "v1",
                    is_active=is_act,
                )
                db.add(db_obj)
            else:
                db_obj.title = doc.title
                db_obj.authority_status = auth_str
                db_obj.current_version_id = doc.current_version_id
                db_obj.is_active = is_act

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"\n[save_document Error]: {e}\n")
        finally:
            db.close()
        return doc


    def get_document(self, doc_id: str) -> Optional[CivicDocument]:
        doc = self._documents.get(doc_id)
        if doc:
            return doc
        db = SessionLocal()
        try:
            db_obj = db.query(RAGDocumentModel).filter_by(document_id=doc_id).first()
            if db_obj:
                now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                try:
                    dt = DocumentType(db_obj.document_type)
                except Exception:
                    dt = DocumentType.POLICY
                try:
                    auth = AuthorityStatus(db_obj.authority_status)
                except Exception:
                    auth = AuthorityStatus.PROVISIONAL
                try:
                    acc = AccessLevel(db_obj.access_level)
                except Exception:
                    acc = AccessLevel.PUBLIC

                doc = CivicDocument(
                    document_id=db_obj.document_id,
                    title=db_obj.title,
                    issuing_authority=db_obj.issuing_authority,
                    jurisdiction_id=db_obj.jurisdiction_id,
                    document_type=dt,
                    authority_status=auth,
                    access_level=acc,
                    source_reference=db_obj.source_reference,
                    current_version_id=db_obj.current_version_id,

                    created_at=now_str,
                    updated_at=now_str,
                )
                self._documents[doc.document_id] = doc
            return doc
        except Exception as e:
            print(f"\n[get_document Error]: {e}\n")
            return None
        finally:
            db.close()


    def list_documents(self) -> List[CivicDocument]:
        if not self._documents:
            db = SessionLocal()
            try:
                records = db.query(RAGDocumentModel).all()
                for db_obj in records:
                    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    try:
                        dt = DocumentType(db_obj.document_type)
                    except Exception:
                        dt = DocumentType.POLICY
                    try:
                        auth = AuthorityStatus(db_obj.authority_status)
                    except Exception:
                        auth = AuthorityStatus.PROVISIONAL
                    try:
                        acc = AccessLevel(db_obj.access_level)
                    except Exception:
                        acc = AccessLevel.PUBLIC

                    doc = CivicDocument(
                        document_id=db_obj.document_id,
                        title=db_obj.title,
                        issuing_authority=db_obj.issuing_authority,
                        jurisdiction_id=db_obj.jurisdiction_id,
                        document_type=dt,
                        authority_status=auth,
                        access_level=acc,
                        source_reference=db_obj.source_reference,
                        current_version_id=db_obj.current_version_id,
                        created_at=now_str,
                        updated_at=now_str,
                    )
                    self._documents[doc.document_id] = doc
            except Exception:
                db.rollback()
            finally:
                db.close()
        return list(self._documents.values())

    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        chk = self._chunks.get(chunk_id)
        if chk:
            return chk
        db = SessionLocal()
        try:
            db_obj = db.query(RAGChunkModel).filter_by(chunk_id=chunk_id).first()
            if db_obj:
                now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                try:
                    auth = AuthorityStatus(db_obj.authority_status)
                except Exception:
                    auth = AuthorityStatus.PROVISIONAL
                try:
                    acc = AccessLevel(db_obj.access_level)
                except Exception:
                    acc = AccessLevel.PUBLIC

                chk = DocumentChunk(
                    chunk_id=db_obj.chunk_id,
                    document_id=db_obj.document_id,
                    version_id=db_obj.version_id,
                    chunk_index=db_obj.chunk_index,
                    section_title=db_obj.section_title or "",
                    page_number=db_obj.page_number,
                    content_text=db_obj.content_text,
                    token_count=db_obj.token_count,
                    jurisdiction_id=db_obj.jurisdiction_id,
                    authority_status=auth,
                    access_level=acc,
                    created_at=now_str,
                )
                self._chunks[chk.chunk_id] = chk
            return chk
        except Exception as e:
            print(f"\n[get_chunk Error]: {e}\n")
            return None
        finally:
            db.close()

    def get_embedding(self, chunk_id: str) -> Optional[ChunkEmbedding]:
        emb = self._embeddings.get(chunk_id)
        if emb:
            return emb
        db = SessionLocal()
        try:
            db_obj = db.query(RAGEmbeddingModel).filter_by(chunk_id=chunk_id).first()
            if db_obj:
                emb = ChunkEmbedding(
                    embedding_id=f"emb_{db_obj.chunk_id}",
                    chunk_id=db_obj.chunk_id,
                    dimensions=db_obj.dimensions,
                    vector=db_obj.vector_json or [],
                )
                self._embeddings[emb.chunk_id] = emb
            return emb
        except Exception as e:
            print(f"\n[get_embedding Error]: {e}\n")
            return None
        finally:
            db.close()




    def deactivate_document(self, doc_id: str) -> Optional[CivicDocument]:
        doc = self._documents.get(doc_id)
        if not doc:
            return None
        doc.authority_status = AuthorityStatus.INACTIVE
        doc.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._documents[doc_id] = doc
        self.save_document(doc)

        for chk in self._chunks.values():
            if chk.document_id == doc_id:
                chk.authority_status = AuthorityStatus.INACTIVE
                db = SessionLocal()
                try:
                    db_obj = db.query(RAGChunkModel).filter_by(chunk_id=chk.chunk_id).first()
                    if db_obj:
                        db_obj.authority_status = "INACTIVE"
                        db.commit()
                except Exception:
                    db.rollback()
                finally:
                    db.close()

        return doc



    def save_version(self, version: DocumentVersion) -> DocumentVersion:
        self._versions[version.version_id] = version
        db = SessionLocal()
        try:
            db_obj = db.query(RAGDocumentVersionModel).filter_by(version_id=version.version_id).first()
            if not db_obj:
                db_obj = RAGDocumentVersionModel(
                    version_id=version.version_id,
                    document_id=version.document_id,
                    version_number=version.version_number,
                    file_name=version.file_name,
                    sha256_checksum=version.checksum,
                )
                db.add(db_obj)
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        doc = self._documents.get(version.document_id)
        if doc:
            doc.current_version_id = version.version_id
            doc.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self._documents[doc.document_id] = doc
            self.save_document(doc)
        return version


    def get_version(self, version_id: str) -> Optional[DocumentVersion]:
        return self._versions.get(version_id)

    def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            db = SessionLocal()
            try:
                auth_str = chunk.authority_status.value if hasattr(chunk.authority_status, "value") else str(chunk.authority_status)
                access_str = chunk.access_level.value if hasattr(chunk.access_level, "value") else str(chunk.access_level)
                db_obj = db.query(RAGChunkModel).filter_by(chunk_id=chunk.chunk_id).first()
                if not db_obj:
                    db_obj = RAGChunkModel(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        version_id=chunk.version_id,
                        chunk_index=chunk.chunk_index,
                        section_title=chunk.section_title,
                        page_number=chunk.page_number,
                        content_text=chunk.content_text,
                        token_count=chunk.token_count,
                        jurisdiction_id=chunk.jurisdiction_id,
                        authority_status=auth_str,
                        access_level=access_str,
                    )
                    db.add(db_obj)
                    db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()

    def save_embeddings(self, embeddings: List[ChunkEmbedding]) -> None:
        for emb in embeddings:
            self._embeddings[emb.chunk_id] = emb
            db = SessionLocal()
            try:
                db_obj = db.query(RAGEmbeddingModel).filter_by(chunk_id=emb.chunk_id).first()
                if not db_obj:
                    db_obj = RAGEmbeddingModel(
                        chunk_id=emb.chunk_id,
                        dimensions=emb.dimensions,
                        vector_json=emb.vector,
                    )
                    db.add(db_obj)
                    db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()



    def get_filtered_chunks(
        self,
        jurisdiction_id: Optional[str] = None,
        user_access_level: AccessLevel = AccessLevel.PUBLIC,
    ) -> List[Tuple[DocumentChunk, List[float]]]:
        role_ranks = {
            AccessLevel.PUBLIC: 1,
            AccessLevel.OPERATOR: 2,
            AccessLevel.SUPERVISOR: 3,
            AccessLevel.ADMIN: 4,
        }
        max_rank = role_ranks.get(user_access_level, 1)

        if not self._chunks:
            db = SessionLocal()
            try:
                db_chunks = db.query(RAGChunkModel).all()
                for c in db_chunks:
                    try: auth = AuthorityStatus(c.authority_status)
                    except: auth = AuthorityStatus.PROVISIONAL
                    try: acc = AccessLevel(c.access_level)
                    except: acc = AccessLevel.PUBLIC
                    chk = DocumentChunk(
                        chunk_id=c.chunk_id,
                        document_id=c.document_id,
                        version_id=c.version_id,
                        chunk_index=c.chunk_index,
                        section_title=c.section_title or "",
                        page_number=c.page_number,
                        content_text=c.content_text,
                        token_count=c.token_count,
                        jurisdiction_id=c.jurisdiction_id,
                        authority_status=auth,
                        access_level=acc,
                        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
                    )
                    self._chunks[chk.chunk_id] = chk
                
                db_embs = db.query(RAGEmbeddingModel).all()
                for e in db_embs:
                    emb = ChunkEmbedding(
                        embedding_id=f"emb_{e.chunk_id}",
                        chunk_id=e.chunk_id,
                        dimensions=e.dimensions,
                        vector=e.vector_json or []
                    )
                    self._embeddings[emb.chunk_id] = emb
            except Exception as e:
                print(f"[get_filtered_chunks DB Load Error]: {e}")
            finally:
                db.close()

        results: List[Tuple[DocumentChunk, List[float]]] = []

        for chunk in self._chunks.values():
            if chunk.authority_status == AuthorityStatus.INACTIVE:
                continue

            chunk_rank = role_ranks.get(chunk.access_level, 1)
            if chunk_rank > max_rank:
                continue

            if jurisdiction_id:
                if chunk.jurisdiction_id and chunk.jurisdiction_id != "*" and chunk.jurisdiction_id != jurisdiction_id:
                    continue

            emb = self._embeddings.get(chunk.chunk_id)
            if emb and emb.vector:
                results.append((chunk, emb.vector))

        return results

    def clear(self) -> None:
        self._documents.clear()
        self._versions.clear()
        self._chunks.clear()
        self._embeddings.clear()
        db = SessionLocal()
        try:
            db.query(RAGEmbeddingModel).delete()
            db.query(RAGChunkModel).delete()
            db.query(RAGDocumentVersionModel).delete()
            db.query(RAGDocumentModel).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


rag_vector_store = RAGVectorStore()

