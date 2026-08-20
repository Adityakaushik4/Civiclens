from typing import List, Optional
from app.rag.schemas import (
    AuthorityStatus,
    AccessLevel,
    Citation,
    GroundedQARequest,
    GroundedQAResponse,
    DocumentChunk,
)
from app.rag.retrieval import rag_retrieval_engine
from app.rag.store import rag_vector_store
from app.llm import get_llm_provider


class RAGGenerationEngine:
    """Grounded Generation and Citation Engine enforcing strict evidence thresholding and zero-hallucination fallback."""

    def generate_grounded_answer(self, request: GroundedQARequest) -> GroundedQAResponse:
        # 1. Retrieve Candidate Chunks
        candidates = rag_retrieval_engine.retrieve_candidate_chunks(
            query=request.query,
            jurisdiction_id=request.jurisdiction_id,
            access_level=request.access_level,
            top_k=request.top_k,
        )

        # 2. Relevance Sufficiency Check
        if not candidates:
            return GroundedQAResponse(
                query=request.query,
                answer="Insufficient authoritative information.",
                evidence_found=False,
                citations=[],
                retrieved_chunks_count=0,
            )

        top_chunk, top_score = candidates[0]
        # Strict threshold check: If top relevance score is too low, refuse to answer
        if top_score < 0.15:
            return GroundedQAResponse(
                query=request.query,
                answer="Insufficient authoritative information.",
                evidence_found=False,
                citations=[],
                retrieved_chunks_count=len(candidates),
            )

        # 3. Construct Context Block & Build Citations
        citations: List[Citation] = []
        context_snippets: List[str] = []

        for chunk, score in candidates:
            doc = rag_vector_store.get_document(chunk.document_id)
            version = rag_vector_store.get_version(chunk.version_id)

            doc_title = doc.title if doc else "Municipal Policy Document"
            issuing_auth = doc.issuing_authority if doc else "Municipal Authority"
            ver_str = f"v{version.version_number}" if version else "v1.0"
            src_ref = doc.source_reference if doc and getattr(doc, "source_reference", None) else "Unknown Source"

            citation = Citation(
                document_title=doc_title,
                issuing_authority=issuing_auth,
                version=ver_str,
                section_title=chunk.section_title or "General Section",
                page_number=chunk.page_number or 1,
                source_reference=src_ref,
                authority_status=chunk.authority_status,
                chunk_id=chunk.chunk_id,
            )
            citations.append(citation)

            snippet = f"[Document: {doc_title} | Section: {chunk.section_title or 'Main'} | Ref: {src_ref}]\n{chunk.content_text}"
            context_snippets.append(snippet)

        # 4. Prompt Synthesis with XML Data Sandbox Defense
        context_block = "\n\n".join(context_snippets)
        prompt = (
            f"You are CivicLens Grounded Policy Assistant. Answer the user question strictly using ONLY the provided authoritative context data.\n"
            f"If the context data does not contain enough information to answer the question accurately, respond with EXACTLY: 'Insufficient authoritative information.'\n"
            f"Do NOT use external knowledge. Do NOT speculate.\n\n"
            f"<CIVIC_CONTEXT_DATA>\n{context_block}\n</CIVIC_CONTEXT_DATA>\n\n"
            f"User Question: {request.query}\n"
            f"Grounded Answer:"
        )

        try:
            llm_provider = get_llm_provider()
            raw_answer = llm_provider.generate_response(prompt)
            answer_text = raw_answer.strip()
        except Exception as e:
            print(f"[Generation Exception] {e}")
            # Deterministic fallback synthesis if LLM provider offline
            best_chunk = candidates[0][0]
            answer_text = f"According to {citations[0].document_title} ({citations[0].source_reference}): {best_chunk.content_text}"

        return GroundedQAResponse(
            query=request.query,
            answer=answer_text,
            evidence_found=True,
            citations=citations,
            retrieved_chunks_count=len(candidates),
        )


rag_generation_engine = RAGGenerationEngine()
