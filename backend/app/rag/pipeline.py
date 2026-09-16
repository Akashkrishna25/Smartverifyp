"""
SmartVerify RAG Pipeline — Main Orchestrator
=============================================
This is the top-level entry point for the Hybrid RAG + Reranking module.

The single public function is:

    smartverify_rag(application_id, query, db, top_k=5)

COMPLETE FLOW:
    1. fetch_loan_data()         → Query PostgreSQL for all application data
    2. build_documents()         → Convert DB records to text chunks
    3. HybridSearch.search()     → Run BM25 + FAISS → RRF fusion
    4. CrossEncoderReranker()    → Rerank candidates for precision
    5. Return evidence JSON       → Structured, ready for VerificationEngine

WHAT THIS MODULE DOES NOT DO:
    - Does NOT approve or reject loans
    - Does NOT store any data
    - Does NOT modify the database
    - Does NOT make any decisions

This module is purely an EVIDENCE RETRIEVAL layer.
The VerificationEngine and DecisionEngine use this evidence to make decisions.

OUTPUT FORMAT:
    {
        "application_id": 5,
        "query": "What is the applicant income?",
        "total_chunks_indexed": 24,
        "evidence": [
            {
                "source": "income_info",
                "document_type": "income",
                "field": "monthly_income",
                "text": "Applicant Rahul Kumar's verified monthly income is Rs. 48,000.",
                "score": 7.2341,
                "rrf_score": 0.031746
            },
            ...
        ]
    }
"""

import logging
from typing import List, Dict, Any
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.rag.document_builder import build_documents
from app.rag.hybrid_search import HybridSearch
from app.rag.reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)


def smartverify_rag(
    application_id: int,
    query: str,
    db: Session,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Run the complete Hybrid RAG + Reranking pipeline for a loan application.

    Args:
        application_id : The ID from the 'applications' table (your primary key)
        query          : A natural language question about the application.
                         Examples:
                           - "What is the applicant's income?"
                           - "Is KYC verified?"
                           - "What is the requested loan amount?"
                           - "What is the vehicle verification status?"
                           - "What information supports this loan application?"
        db             : SQLAlchemy database session (injected via FastAPI Depends)
        top_k          : Number of top evidence chunks to return (default: 5)

    Returns:
        A dictionary with the structured evidence response (see module docstring).
        Returns an error dict if the application is not found or data is missing.

    IMPORTANT:
        This function only retrieves and ranks evidence.
        It does NOT make any loan approval or rejection decision.
    """
    logger.info(
        f"[RAG] Starting pipeline for application_id={application_id}, "
        f"query='{query}'"
    )

    # ── Step 1: Build Documents from Database ──────────────────────────
    # This queries the database and converts all records into text chunks.
    # No hardcoded values — everything comes from your PostgreSQL tables.
    chunks = build_documents(application_id, db)

    if not chunks:
        logger.warning(f"[RAG] No chunks built for application_id={application_id}")
        return {
            "application_id" : application_id,
            "query"          : query,
            "total_chunks_indexed": 0,
            "evidence"       : [],
            "error"          : (
                f"No data found for application_id={application_id}. "
                "Please ensure the application exists in the database."
            ),
        }

    total_chunks = len(chunks)
    logger.info(f"[RAG] Built {total_chunks} document chunks.")

    # ── Step 2: Hybrid Search (BM25 + FAISS → RRF) ────────────────────
    # We retrieve more candidates than top_k so the reranker has
    # enough options to pick the truly best ones.
    num_candidates = min(max(top_k * 3, 15), total_chunks)

    hybrid = HybridSearch(chunks)
    fused_candidates = hybrid.search(
        query=query,
        top_k=num_candidates,
        bm25_candidates=num_candidates,
        faiss_candidates=num_candidates,
    )

    logger.info(f"[RAG] Hybrid search returned {len(fused_candidates)} candidates.")

    # ── Step 3: Cross-Encoder Reranking ───────────────────────────────
    reranker = CrossEncoderReranker()
    final_evidence = reranker.rerank(
        query=query,
        candidates=fused_candidates,
        top_k=top_k,
    )

    logger.info(
        f"[RAG] Pipeline complete. Returning {len(final_evidence)} evidence chunks."
    )

    return {
        "application_id"      : application_id,
        "query"               : query,
        "total_chunks_indexed": total_chunks,
        "evidence"            : final_evidence,
    }


def batch_smartverify_rag(
    application_id: int,
    queries: List[str],
    db: Session,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Run the RAG pipeline for multiple queries on the same application.

    This is more efficient than calling smartverify_rag() multiple times
    because it builds the document index ONCE and reuses it for all queries.

    Useful for generating a comprehensive evidence report during viva demo.

    Args:
        application_id : Application ID
        queries        : List of natural language queries
        db             : SQLAlchemy database session
        top_k          : Top results per query

    Returns:
        A list of result dicts, one per query.
    """
    logger.info(
        f"[RAG] Batch pipeline for application_id={application_id}, "
        f"{len(queries)} queries."
    )

    # Build chunks once — shared across all queries
    chunks = build_documents(application_id, db)

    if not chunks:
        return [
            {
                "application_id" : application_id,
                "query"          : q,
                "total_chunks_indexed": 0,
                "evidence"       : [],
                "error"          : f"No data found for application_id={application_id}",
            }
            for q in queries
        ]

    total_chunks = len(chunks)

    # Build indexes once
    num_candidates = min(max(top_k * 3, 15), total_chunks)
    hybrid = HybridSearch(chunks)
    reranker = CrossEncoderReranker()

    results = []
    for query in queries:
        candidates = hybrid.search(
            query=query,
            top_k=num_candidates,
            bm25_candidates=num_candidates,
            faiss_candidates=num_candidates,
        )
        evidence = reranker.rerank(query=query, candidates=candidates, top_k=top_k)
        results.append({
            "application_id"      : application_id,
            "query"               : query,
            "total_chunks_indexed": total_chunks,
            "evidence"            : evidence,
        })

    return results
