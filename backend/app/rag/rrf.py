"""
Reciprocal Rank Fusion (RRF)
=============================
WHAT IS RRF?
    RRF is a simple but powerful algorithm to combine results from multiple
    ranked lists (e.g., from BM25 and FAISS) into a single unified ranking.

THE PROBLEM IT SOLVES:
    - BM25 gives scores like 3.45, 2.10, 1.67, ...
    - FAISS gives scores like 0.92, 0.87, 0.65, ...
    These scores are in completely different scales, so you CAN'T simply add them.
    A BM25 score of 3.45 does NOT mean the same as a FAISS score of 3.45.

THE RRF FORMULA:
    For each document d, its RRF score is:

        RRF(d) = sum over all lists L: 1 / (k + rank_of_d_in_L)

    where k is a constant (typically 60) that prevents very high scores
    for documents at rank 1.

EXAMPLE:
    Document A is rank 1 in BM25 and rank 3 in FAISS:
        RRF(A) = 1/(60+1) + 1/(60+3) = 0.01639 + 0.01587 = 0.03226

    Document B is rank 2 in BM25 and rank 1 in FAISS:
        RRF(B) = 1/(60+2) + 1/(60+1) = 0.01613 + 0.01639 = 0.03252

    Document B wins! Even though A was ranked #1 in BM25,
    document B's strong performance across BOTH lists wins overall.

WHY USE RRF?
    - No need to normalise scores (rank positions are universal)
    - Robust: a document that's good in both lists rises to the top
    - Simple to implement and understand
    - Used by Elasticsearch, Vespa, and many production RAG systems

Reference: Cormack, Clarke & Buettcher (2009) "Reciprocal Rank Fusion
outperforms Condorcet and individual Rank Learning Methods"
"""

import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# k constant for RRF — 60 is the standard recommended value from the paper
RRF_K = 60


def reciprocal_rank_fusion(
    *ranked_lists: List[Tuple[int, float, Dict[str, Any]]],
    top_k: int = 20
) -> List[Tuple[int, float, Dict[str, Any]]]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion.

    Args:
        *ranked_lists : Any number of ranked lists.
                        Each list is a list of tuples: (original_index, score, chunk_dict)
                        as returned by BM25Retriever.search() or FAISSStore.search().
        top_k         : Number of top results to return after fusion.

    Returns:
        A single merged and re-ranked list of tuples:
        (original_index, rrf_score, chunk_dict)
        Sorted by rrf_score descending (best first).
    """
    # rrf_scores maps original_index -> cumulative RRF score
    rrf_scores: Dict[int, float] = {}

    # chunk_map maps original_index -> chunk_dict (to look up later)
    chunk_map: Dict[int, Dict[str, Any]] = {}

    for ranked_list in ranked_lists:
        if not ranked_list:
            continue

        for rank_position, (original_index, _score, chunk_dict) in enumerate(ranked_list):
            # rank_position is 0-based, so rank 1 = rank_position 0
            # We use rank_position + 1 to make it 1-based
            rrf_contribution = 1.0 / (RRF_K + rank_position + 1)

            rrf_scores[original_index] = (
                rrf_scores.get(original_index, 0.0) + rrf_contribution
            )
            chunk_map[original_index] = chunk_dict

    # Sort all documents by their accumulated RRF score (highest first)
    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    # Build the output list of (index, rrf_score, chunk_dict)
    results = [
        (idx, score, chunk_map[idx])
        for idx, score in sorted_docs[:top_k]
    ]

    logger.debug(
        f"RRF fusion merged {len(ranked_lists)} lists into {len(results)} results. "
        f"Top RRF score: {results[0][1]:.6f}" if results else
        "RRF fusion produced 0 results."
    )

    return results
