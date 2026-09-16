"""
FAISS Vector Store
==================
WHAT IS FAISS?
    FAISS (Facebook AI Similarity Search) is a library that lets you search
    through thousands of text embeddings very quickly using vector mathematics.

WHAT IS A VECTOR EMBEDDING?
    When a Sentence Transformer model reads "What is the applicant's income?",
    it converts that sentence into a list of 384 numbers (a vector).
    Similar sentences produce vectors that are close to each other in space.

    Example:
    - "applicant monthly salary"    -> [0.2, 0.8, 0.1, ...]
    - "applicant income per month"  -> [0.21, 0.79, 0.12, ...]  <- Very similar!
    - "vehicle registration plate"  -> [0.9, 0.1, 0.7, ...]     <- Very different!

HOW IT WORKS HERE:
    1. All text chunks are converted to vectors using 'all-MiniLM-L6-v2'
       (a small, fast, 384-dimensional model that runs well on CPU).
    2. These vectors are stored in a FAISS index (in memory).
    3. When you query, the query text is also converted to a vector,
       and FAISS finds the chunks whose vectors are most similar (cosine similarity).

STRENGTHS:
    - Understands synonyms and meaning (semantics)
    - "salary" and "income" are treated as similar
    - Handles paraphrasing and varied phrasing

WEAKNESS:
    - May miss exact keyword matches that BM25 would catch
    - Slower than BM25 (but still fast enough for a demo)

Model used: sentence-transformers/all-MiniLM-L6-v2
    - Size: ~80MB
    - Speed: ~14,000 sentences/second on CPU
    - Dimension: 384
"""

import logging
# pyrefly: ignore [missing-import]
import numpy as np
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Lazy imports to avoid slow startup when this module is not needed
_sentence_transformer = None
_faiss = None


def _get_model():
    """Load the SentenceTransformer model once (singleton pattern)."""
    global _sentence_transformer
    if _sentence_transformer is None:
        # pyrefly: ignore [missing-import]
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
        _sentence_transformer = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("SentenceTransformer model loaded successfully.")
    return _sentence_transformer


def _get_faiss():
    """Import FAISS once (singleton pattern)."""
    global _faiss
    if _faiss is None:
        # pyrefly: ignore [missing-import]
        import faiss
        _faiss = faiss
    return _faiss


class FAISSStore:
    """
    In-memory FAISS vector store for semantic search over document chunks.

    Workflow:
        store = FAISSStore(chunks)          # Build index
        results = store.search("income?", top_k=10)   # Query

    The index uses cosine similarity (via L2 normalisation + inner product).
    """

    def __init__(self, chunks: List[Dict[str, Any]]):
        """
        Build the FAISS index from document chunks.

        Args:
            chunks: List of chunk dicts with at least a "text" key.
        """
        if not chunks:
            logger.warning("FAISSStore initialised with empty chunk list.")
            self.chunks = []
            self.index = None
            return

        self.chunks = chunks
        model = _get_model()
        faiss = _get_faiss()

        # Extract all text strings from chunks
        texts = [chunk["text"] for chunk in chunks]

        # Convert texts to embeddings (numpy float32 array)
        # Shape: (num_chunks, 384)
        logger.info(f"Encoding {len(texts)} document chunks into vectors...")
        embeddings = model.encode(
            texts,
            batch_size=32,          # Process 32 sentences at a time
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalise for cosine similarity
        ).astype(np.float32)

        # FAISS IndexFlatIP = Inner Product index
        # With normalised vectors, inner product == cosine similarity
        dimension = embeddings.shape[1]  # Should be 384 for MiniLM
        self.index = faiss.IndexFlatIP(dimension)

        # Add all embeddings to the index
        self.index.add(embeddings)

        logger.info(
            f"FAISS index built: {self.index.ntotal} vectors, dimension={dimension}"
        )

    def search(
        self, query: str, top_k: int = 10
    ) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        Perform semantic similarity search for a query string.

        Args:
            query : Natural language query
            top_k : Number of top results to return

        Returns:
            List of tuples: (original_index, similarity_score, chunk_dict)
            Sorted by similarity score descending (most similar first).
        """
        if not self.index or not self.chunks:
            logger.warning("FAISS search called but index is empty.")
            return []

        model = _get_model()

        # Encode the query into a vector
        query_embedding = model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        ).astype(np.float32)

        # Ensure top_k does not exceed the number of indexed documents
        k = min(top_k, self.index.ntotal)

        # Search the FAISS index
        # scores: shape (1, k) — similarity scores
        # indices: shape (1, k) — indices into self.chunks
        scores, indices = self.index.search(query_embedding, k)

        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue  # FAISS returns -1 for empty slots
            results.append((int(idx), float(score), self.chunks[idx]))

        logger.debug(
            f"FAISS search for '{query}' returned {len(results)} results "
            f"(top score: {results[0][1]:.4f})" if results else
            f"FAISS search for '{query}' returned 0 results."
        )

        return results
