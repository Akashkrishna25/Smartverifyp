"""
Cross-Encoder Reranker
=======================
WHAT IS A CROSS-ENCODER?
    A Cross-Encoder is a neural network that takes BOTH the query AND a document
    as input at the same time and outputs a single relevance score.

    This is different from a Bi-Encoder (like Sentence Transformers):
    - Bi-Encoder: encodes query and document SEPARATELY → fast but less accurate
    - Cross-Encoder: reads query + document TOGETHER → slower but much more accurate

    The Cross-Encoder can "understand" exactly how relevant a specific document
    is to a specific query because it sees both at once.

WHY DO WE NEED RERANKING?
    After BM25 + FAISS + RRF, we have ~10–20 candidate documents.
    These might be good, but their ranking is not perfectly accurate.

    The Cross-Encoder re-scores each (query, document) pair with much
    higher accuracy and reorders them.

    Think of it as two stages:
        Stage 1: Fast retrieval (BM25 + FAISS) → Get 20 candidates quickly
        Stage 2: Accurate reranking (Cross-Encoder) → Reorder the 20 precisely

MODEL USED:
    cross-encoder/ms-marco-MiniLM-L-6-v2
    - Trained on MS MARCO (a massive question-answering dataset)
    - Size: ~67MB
    - Runs on CPU in ~0.5s for 20 documents
    - Returns a raw score (higher = more relevant)

IMPORTANT:
    The reranker only reorders the evidence.
    It does NOT make any loan approval or rejection decision.
"""

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Lazy-loaded singleton — avoids slow model loading on every request
_cross_encoder = None


def _get_cross_encoder():
    """Load the Cross-Encoder model once and cache it."""
    global _cross_encoder
    if _cross_encoder is None:
        # pyrefly: ignore [missing-import]
        from sentence_transformers.cross_encoder import CrossEncoder
        logger.info("Loading Cross-Encoder model (ms-marco-MiniLM-L-6-v2)...")
        _cross_encoder = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            max_length=512,   # Maximum token length
        )
        logger.info("Cross-Encoder model loaded successfully.")
    return _cross_encoder


class CrossEncoderReranker:
    """
    Reranks a list of retrieved document chunks using a Cross-Encoder.

    Usage:
        reranker = CrossEncoderReranker()
        reranked = reranker.rerank(query, candidates, top_k=5)
    """

    def rerank(
        self,
        query: str,
        candidates: List[Tuple[int, float, Dict[str, Any]]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidate chunks by their relevance to the query.

        Args:
            query      : The user's natural language query
            candidates : List of tuples (original_index, rrf_score, chunk_dict)
                         as returned by HybridSearch.search() or RRF fusion.
            top_k      : Number of top results to return after reranking.

        Returns:
            A list of result dicts (top_k items), each containing:
            {
                "source"           : str  — which section this came from
                "document_type"    : str  — broad type (loan, applicant, etc.)
                "field"            : str  — specific field name
                "text"             : str  — the actual evidence text
                "score"            : float — Cross-Encoder relevance score
                "rrf_score"        : float — the RRF score before reranking
                "application_id"   : int
            }
        """
        if not candidates:
            logger.warning("Reranker called with empty candidate list.")
            return []

        try:
            model = _get_cross_encoder()
        except Exception as e:
            logger.error(f"Cross-Encoder model could not be loaded: {e}. "
                         f"Falling back to RRF-only ranking.")
            # Graceful fallback: return candidates in RRF order without reranking
            return self._fallback_results(candidates, top_k)

        # Build (query, document_text) pairs for the Cross-Encoder
        pairs = [
            (query, chunk["text"])
            for (_idx, _rrf_score, chunk) in candidates
        ]

        # Score all pairs — the Cross-Encoder reads query+doc together
        # Returns a list of floats (higher = more relevant)
        try:
            scores = model.predict(pairs, show_progress_bar=False)
        except Exception as e:
            logger.error(f"Cross-Encoder prediction failed: {e}. Falling back to RRF order.")
            return self._fallback_results(candidates, top_k)

        # Combine: attach Cross-Encoder score to each candidate
        scored = []
        for (original_idx, rrf_score, chunk), ce_score in zip(candidates, scores):
            scored.append({
                "source"          : chunk.get("source", "unknown"),
                "document_type"   : chunk.get("document_type", "unknown"),
                "field"           : chunk.get("field", "unknown"),
                "text"            : chunk["text"],
                "score"           : round(float(ce_score), 4),
                "rrf_score"       : round(float(rrf_score), 6),
                "application_id"  : chunk.get("application_id"),
            })

        # Sort by Cross-Encoder score (highest first)
        scored.sort(key=lambda x: x["score"], reverse=True)

        top_results = scored[:top_k]

        logger.info(
            f"Cross-Encoder reranked {len(candidates)} candidates. "
            f"Returning top {len(top_results)}. "
            f"Top score: {top_results[0]['score']:.4f}" if top_results else
            "Reranker returned 0 results."
        )

        return top_results

    def _fallback_results(
        self,
        candidates: List[Tuple[int, float, Dict[str, Any]]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        Fallback: return candidates in RRF score order (no Cross-Encoder scoring).
        Used when the Cross-Encoder model fails to load or predict.
        """
        results = []
        for (_idx, rrf_score, chunk) in candidates[:top_k]:
            results.append({
                "source"          : chunk.get("source", "unknown"),
                "document_type"   : chunk.get("document_type", "unknown"),
                "field"           : chunk.get("field", "unknown"),
                "text"            : chunk["text"],
                "score"           : round(float(rrf_score), 6),
                "rrf_score"       : round(float(rrf_score), 6),
                "application_id"  : chunk.get("application_id"),
            })
        return results
