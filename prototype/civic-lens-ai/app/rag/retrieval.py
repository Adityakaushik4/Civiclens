import math
from typing import List, Tuple, Optional
from app.rag.schemas import DocumentChunk, AccessLevel, AuthorityStatus
from app.rag.store import rag_vector_store
from app.embeddings import get_embedding_provider


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two 3072-dimensional vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def bm25_lexical_score(query: str, text: str) -> float:
    """Computes basic BM25 keyword matching score."""
    q_words = set(re.findall(r"\w+", query.lower()))
    if not q_words:
        return 0.0
    t_words = re.findall(r"\w+", text.lower())
    if not t_words:
        return 0.0
    match_count = sum(1 for w in t_words if w in q_words)
    return float(match_count) / (len(t_words) + 10.0)


import re


class RAGRetrievalEngine:
    """Hybrid Retrieval Engine combining 3072-dim Cosine Similarity and Lexical BM25 via Reciprocal Rank Fusion."""

    def retrieve_candidate_chunks(
        self,
        query: str,
        jurisdiction_id: Optional[str] = None,
        access_level: AccessLevel = AccessLevel.PUBLIC,
        top_k: int = 5,
    ) -> List[Tuple[DocumentChunk, float]]:
        # 1. Pre-filtered candidate chunks with vectors
        candidates = rag_vector_store.get_filtered_chunks(jurisdiction_id, access_level)
        if not candidates:
            return []

        # 2. Embed Query (3072 dimensions)
        emb_provider = get_embedding_provider()
        try:
            query_vector = emb_provider.get_embedding(query)
        except Exception:
            query_vector = [0.0] * 3072

        # 3. Compute Cosine & BM25 Scores
        vector_scored: List[Tuple[DocumentChunk, float]] = []
        bm25_scored: List[Tuple[DocumentChunk, float]] = []

        for chunk, vector in candidates:
            c_score = cosine_similarity(query_vector, vector)
            b_score = bm25_lexical_score(query, chunk.content_text)
            vector_scored.append((chunk, c_score))
            bm25_scored.append((chunk, b_score))

        # Sort by vector and BM25 ranks
        vector_ranked = sorted(vector_scored, key=lambda x: x[1], reverse=True)
        bm25_ranked = sorted(bm25_scored, key=lambda x: x[1], reverse=True)

        vec_ranks = {chunk.chunk_id: rank for rank, (chunk, _) in enumerate(vector_ranked, start=1)}
        bm25_ranks = {chunk.chunk_id: rank for rank, (chunk, _) in enumerate(bm25_ranked, start=1)}

        # 4. Compute Reciprocal Rank Fusion (RRF) & Apply Authority Reranking Booster
        rrf_results: List[Tuple[DocumentChunk, float]] = []
        q_clean = query.lower()

        for chunk, c_score in vector_scored:
            v_rank = vec_ranks.get(chunk.chunk_id, 100)
            b_rank = bm25_ranks.get(chunk.chunk_id, 100)

            # RRF score formula
            rrf = (1.0 / (60.0 + v_rank)) + (1.0 / (60.0 + b_rank))

            # Reranker multipliers
            auth_multiplier = 1.20 if chunk.authority_status == AuthorityStatus.AUTHORITATIVE else 1.0
            sec_match_multiplier = 1.15 if chunk.section_title and any(w in chunk.section_title.lower() for w in q_clean.split()) else 1.0

            final_score = rrf * auth_multiplier * sec_match_multiplier
            # Blend with raw cosine similarity score for relevance thresholding
            blended_score = (final_score * 30.0) + (c_score * 0.70)
            rrf_results.append((chunk, blended_score))

        # Sort by final score
        sorted_candidates = sorted(rrf_results, key=lambda x: x[1], reverse=True)
        return sorted_candidates[:top_k]


rag_retrieval_engine = RAGRetrievalEngine()
