"""
BM25 Keyword Retriever
======================
WHAT IS BM25?
    BM25 (Best Match 25) is a classic keyword search algorithm used by
    search engines like Elasticsearch and Lucene.

    Given a query like "What is the applicant income?", BM25 breaks it
    into words (tokens) and finds documents that contain those words,
    ranking them by how often and how uniquely they appear.

HOW IT WORKS HERE:
    1. All text chunks from the document builder are tokenized (split into words).
    2. A BM25 index is built from those tokens.
    3. When you run a query, BM25 scores each chunk and returns the top-k.

STRENGTHS:
    - Very fast
    - Great at exact keyword matches (e.g., "PAN number", "Aadhaar", "KYC")
    - Works without any ML models or GPU

WEAKNESS:
    - Cannot understand meaning (semantics)
    - "income" and "salary" are treated as completely different words

That's why we also use FAISS (semantic search) and combine them.
"""

import logging
from typing import List, Dict, Any, Tuple

# pyrefly: ignore [missing-import]
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    """
    Simple tokenizer: lowercase, split on spaces, remove short tokens.
    In a production system you'd use NLTK or SpaCy for better results,
    but this is sufficient for a final-year project.
    """
    return [
        word.lower().strip(".,;:!?\"'()")
        for word in text.split()
        if len(word) > 2  # skip very short words like "a", "is", "the"
    ]


class BM25Retriever:
    """
    Wraps the rank-bm25 library to provide keyword search over
    a list of document chunks.

    Usage:
        retriever = BM25Retriever(chunks)
        results = retriever.search("What is the applicant income?", top_k=10)
    """

    def __init__(self, chunks: List[Dict[str, Any]]):
        """
        Build the BM25 index from the provided chunks.

        Args:
            chunks: List of chunk dicts from document_builder.build_documents()
                    Each must have a "text" key.
        """
        if not chunks:
            logger.warning("BM25Retriever initialised with empty chunk list.")
            self.chunks = []
            self.bm25 = None
            return

        self.chunks = chunks

        # Tokenize every chunk's text for the BM25 index
        tokenized_corpus = [_tokenize(chunk["text"]) for chunk in chunks]

        # BM25Okapi is the standard BM25 variant (Okapi BM25)
        # k1=1.5 and b=0.75 are standard default parameters
        self.bm25 = BM25Okapi(tokenized_corpus, k1=1.5, b=0.75)

        logger.info(f"BM25 index built with {len(chunks)} documents.")

    def search(
        self, query: str, top_k: int = 10
    ) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        Search the BM25 index for the most relevant chunks.

        Args:
            query : The search query string (e.g., "applicant income verified?")
            top_k : Maximum number of results to return

        Returns:
            A list of tuples: (original_index, bm25_score, chunk_dict)
            Sorted by score in descending order (highest score first).
        """
        if not self.bm25 or not self.chunks:
            logger.warning("BM25 search called but index is empty.")
            return []

        # Tokenize the query using the same tokenizer as the corpus
        query_tokens = _tokenize(query)

        if not query_tokens:
            logger.warning(f"Query '{query}' produced no tokens after tokenization.")
            return []

        # Get BM25 scores for all documents
        scores = self.bm25.get_scores(query_tokens)

        # Create (index, score) pairs and sort by score (descending)
        scored_docs = [
            (idx, float(score), self.chunks[idx])
            for idx, score in enumerate(scores)
            if score > 0  # skip documents with zero relevance
        ]
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        top_results = scored_docs[:top_k]

        logger.debug(
            f"BM25 search for '{query}' returned {len(top_results)} results "
            f"(top score: {top_results[0][1]:.4f})" if top_results else
            f"BM25 search for '{query}' returned 0 results."
        )

        return top_results
