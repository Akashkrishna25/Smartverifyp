"""
Hybrid Search Orchestrator
===========================
WHAT IT DOES:
    Runs BM25 (keyword search) and FAISS (semantic search) in parallel
    on the same set of document chunks, then hands both result lists
    to the RRF fusion module.

WHY HYBRID?
    No single retrieval method is perfect:

    ┌─────────────────┬────────────────────────┬────────────────────────┐
    │                 │ BM25 (Keyword)         │ FAISS (Semantic)       │
    ├─────────────────┼────────────────────────┼────────────────────────┤
    │ Strength        │ Exact keyword matches  │ Meaning / synonyms     │
    │                 │ "KYC", "PAN", "Aadhaar"│ "salary" ≈ "income"   │
    │ Weakness        │ Misses synonyms        │ May miss exact terms   │
    │ Speed           │ Very fast              │ Slower (model inference)│
    └─────────────────┴────────────────────────┴────────────────────────┘

    By running both and combining with RRF, we get the best of both worlds.

FLOW:
    chunks → BM25Retriever ────────────────────┐
                                               ▼
                                         RRF Fusion → Merged Ranked List
                                               ▲
    chunks → FAISSStore ──────────────────────┘
"""

import logging
from typing import List, Dict, Any, Tuple

from app.rag.bm25_retriever import BM25Retriever
from app.rag.faiss_store import FAISSStore
from app.rag.rrf import reciprocal_rank_fusion

logger = logging.getLogger(__name__)


class HybridSearch:
    """
    Hybrid retrieval combining BM25 keyword search and FAISS semantic search.

    Usage:
        hs = HybridSearch(chunks)
        results = hs.search("Is KYC verified?", top_k=10)
    """

    def __init__(self, chunks: List[Dict[str, Any]]):
        """
        Initialise both BM25 and FAISS indexes from the given chunks.

        Args:
            chunks: List of chunk dicts from document_builder.build_documents()
        """
        if not chunks:
            logger.warning("HybridSearch initialised with empty chunk list.")
            self.chunks = []
            self.bm25 = None
            self.faiss_store = None
            return

        self.chunks = chunks

        # Build BM25 index (fast, no ML)
        logger.info("Building BM25 index...")
        self.bm25 = BM25Retriever(chunks)

        # Build FAISS index (uses sentence-transformers)
        logger.info("Building FAISS vector index...")
        self.faiss_store = FAISSStore(chunks)

        logger.info(
            f"HybridSearch ready: {len(chunks)} chunks indexed in BM25 and FAISS."
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
        bm25_candidates: int = 20,
        faiss_candidates: int = 20,
    ) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        Run hybrid retrieval: BM25 + FAISS → RRF fusion.

        Args:
            query            : The natural language search query
            top_k            : Final number of results to return after RRF
            bm25_candidates  : How many candidates BM25 should retrieve (>=top_k)
            faiss_candidates : How many candidates FAISS should retrieve (>=top_k)

        Returns:
            List of tuples: (original_index, rrf_score, chunk_dict)
            Sorted by RRF score descending.
        """
        if not self.chunks:
            return []

        # ── Step 1: BM25 Keyword Retrieval ─────────────────────────────
        logger.debug(f"Running BM25 retrieval for: '{query}'")
        bm25_results = self.bm25.search(query, top_k=bm25_candidates)

        # ── Step 2: FAISS Semantic Retrieval ───────────────────────────
        logger.debug(f"Running FAISS retrieval for: '{query}'")
        faiss_results = self.faiss_store.search(query, top_k=faiss_candidates)

        logger.info(
            f"Hybrid retrieval: BM25 returned {len(bm25_results)} results, "
            f"FAISS returned {len(faiss_results)} results."
        )

        # ── Step 3: RRF Fusion ─────────────────────────────────────────
        fused_results = reciprocal_rank_fusion(
            bm25_results,
            faiss_results,
            top_k=top_k,
        )

        logger.info(
            f"After RRF fusion: {len(fused_results)} results for query: '{query}'"
        )

        return fused_results
