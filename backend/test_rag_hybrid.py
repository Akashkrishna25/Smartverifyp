"""
SmartVerify Hybrid RAG Pipeline — Test Script
==============================================
PURPOSE:
    A standalone test script to verify that the entire RAG pipeline
    works correctly without needing to run the FastAPI server.

WHAT IT TESTS:
    1. Database connection to PostgreSQL
    2. fetch_loan_data() — retrieves application data
    3. build_documents() — converts DB records to text chunks
    4. BM25Retriever.search() — keyword retrieval
    5. FAISSStore.search() — semantic/vector retrieval
    6. RRF fusion — combines rankings
    7. Cross-Encoder reranking — precision scoring
    8. Final smartverify_rag() — full end-to-end pipeline

HOW TO RUN:
    cd backend
    python test_rag_hybrid.py

    OR specify application_id and query:
    python test_rag_hybrid.py --app-id 1 --query "Is KYC verified?"

REQUIREMENTS:
    pip install rank-bm25 faiss-cpu sentence-transformers

NOTE:
    This script connects directly to the database using the same
    DATABASE_URL from your .env file. No FastAPI server needed.
"""

import os
import sys
import argparse
import time
import logging

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# -- Setup Python path so we can import app modules ----------------------------
# This adds the backend/ directory to the path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

# Change working directory to backend/ so that pydantic-settings can
# locate the .env file automatically (it reads env_file = ".env").
# No manual dotenv loading needed — pydantic_settings handles it.
os.chdir(BACKEND_DIR)

# -- Configure logging --------------------------------------------------------─
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_rag_hybrid")

# Suppress noisy library logs during the test
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)
logging.getLogger("faiss").setLevel(logging.WARNING)


# -- Helpers for pretty output ------------------------------------------------─

def print_header(title: str):
    width = 70
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_section(title: str):
    print(f"\n-- {title} " + "-" * (60 - len(title)))


def print_evidence(evidence_list: list):
    """Pretty-print a list of evidence chunks."""
    if not evidence_list:
        print("  [WARN]  No evidence returned.")
        return
    for i, ev in enumerate(evidence_list, start=1):
        score = ev.get("score", 0)
        source = ev.get("source", "?")
        field = ev.get("field", "?")
        text = ev.get("text", "")
        print(f"\n  [{i}] Score: {score:.4f}  |  Source: {source}  |  Field: {field}")
        print(f"      Text: {text[:120]}{'...' if len(text) > 120 else ''}")


# -- Main test function --------------------------------------------------------

def run_tests(application_id: int, query: str):
    """Run the full RAG pipeline test suite."""

    print_header(f"SmartVerify Hybrid RAG Test — Application ID: {application_id}")

    # -- STEP 0: Import and connect to database --------------------------------
    print_section("STEP 0: Database Connection")
    t0 = time.time()
    try:
        from app.db.database import SessionLocal
        db = SessionLocal()
        print(f"  [OK] Database session created ({time.time()-t0:.2f}s)")
    except Exception as e:
        print(f"  [FAIL] Database connection FAILED: {e}")
        print("\n  Make sure DATABASE_URL in .env is correct and the database is running.")
        sys.exit(1)

    # -- STEP 1: Test fetch_loan_data() --------------------------------------─
    print_section("STEP 1: fetch_loan_data()")
    t1 = time.time()
    try:
        from app.rag.document_builder import fetch_loan_data
        data = fetch_loan_data(application_id, db)

        if not data:
            print(f"  [FAIL] No data found for application_id={application_id}")
            print(f"     Please use a valid application_id from your database.")
            print(f"     Tip: Run 'SELECT id FROM applications LIMIT 5;' in psql")
            db.close()
            sys.exit(1)

        app = data["application"]
        print(f"  [OK] Application found ({time.time()-t1:.2f}s)")
        print(f"     Applicant  : {app.applicant_name or 'Not set'}")
        print(f"     Loan Type  : {app.loan_type or 'Not set'}")
        print(f"     Loan Amount: {app.loan_amount}")
        print(f"     Status     : {app.status}")
        print(f"     Documents  : {len(data['documents'])} uploaded")
        print(f"     KYC Record : {'Yes' if data['gov_verification'] else 'Not done yet'}")
        print(f"     Site Verif.: {'Yes' if data['site_verification'] else 'Not done yet'}")
        print(f"     Joint Apps : {len(data['joint_applicants'])}")
        print(f"     Report     : {'Exists' if data['report'] else 'Not generated yet'}")

    except Exception as e:
        print(f"  [FAIL] fetch_loan_data() FAILED: {e}")
        logger.exception("fetch_loan_data failed")
        db.close()
        sys.exit(1)

    # -- STEP 2: Test build_documents() --------------------------------------─
    print_section("STEP 2: build_documents() — RAG Document Builder")
    t2 = time.time()
    try:
        from app.rag.document_builder import build_documents
        chunks = build_documents(application_id, db)

        if not chunks:
            print(f"  [FAIL] No chunks built. Check document_builder.py")
            db.close()
            sys.exit(1)

        print(f"  [OK] Built {len(chunks)} text chunks ({time.time()-t2:.2f}s)")

        # Show a sample from each source type
        seen_sources = set()
        print(f"\n  Sample chunks (one per source):")
        for chunk in chunks:
            src = chunk["source"]
            if src not in seen_sources:
                seen_sources.add(src)
                text_preview = chunk["text"][:90] + "..." if len(chunk["text"]) > 90 else chunk["text"]
                print(f"    [{src}] {text_preview}")

    except Exception as e:
        print(f"  [FAIL] build_documents() FAILED: {e}")
        logger.exception("build_documents failed")
        db.close()
        sys.exit(1)

    # -- STEP 3: Test BM25 Retrieval ------------------------------------------─
    print_section("STEP 3: BM25Retriever — Keyword Search")
    t3 = time.time()
    try:
        from app.rag.bm25_retriever import BM25Retriever
        bm25 = BM25Retriever(chunks)
        bm25_results = bm25.search(query, top_k=5)

        print(f"  [OK] BM25 returned {len(bm25_results)} results ({time.time()-t3:.2f}s)")
        for rank, (idx, score, chunk) in enumerate(bm25_results, 1):
            text_preview = chunk["text"][:80] + "..." if len(chunk["text"]) > 80 else chunk["text"]
            print(f"    Rank {rank}: score={score:.4f}  [{chunk['source']}]  {text_preview}")

    except Exception as e:
        print(f"  [FAIL] BM25 search FAILED: {e}")
        logger.exception("BM25 failed")

    # -- STEP 4: Test FAISS Retrieval ----------------------------------------─
    print_section("STEP 4: FAISSStore — Semantic Vector Search")
    print("  (First run downloads the model ~80MB — please wait...)")
    t4 = time.time()
    try:
        from app.rag.faiss_store import FAISSStore
        faiss_store = FAISSStore(chunks)
        faiss_results = faiss_store.search(query, top_k=5)

        print(f"  [OK] FAISS returned {len(faiss_results)} results ({time.time()-t4:.2f}s)")
        for rank, (idx, score, chunk) in enumerate(faiss_results, 1):
            text_preview = chunk["text"][:80] + "..." if len(chunk["text"]) > 80 else chunk["text"]
            print(f"    Rank {rank}: score={score:.4f}  [{chunk['source']}]  {text_preview}")

    except Exception as e:
        print(f"  [FAIL] FAISS search FAILED: {e}")
        logger.exception("FAISS failed")
        faiss_results = []

    # -- STEP 5: Test RRF Fusion ----------------------------------------------─
    print_section("STEP 5: Reciprocal Rank Fusion (RRF)")
    t5 = time.time()
    try:
        from app.rag.rrf import reciprocal_rank_fusion
        fused = reciprocal_rank_fusion(bm25_results, faiss_results, top_k=10)

        print(f"  [OK] RRF fusion: {len(fused)} results ({time.time()-t5:.4f}s)")
        for rank, (idx, rrf_score, chunk) in enumerate(fused[:5], 1):
            text_preview = chunk["text"][:80] + "..." if len(chunk["text"]) > 80 else chunk["text"]
            print(f"    Rank {rank}: rrf={rrf_score:.6f}  [{chunk['source']}]  {text_preview}")

    except Exception as e:
        print(f"  [FAIL] RRF fusion FAILED: {e}")
        logger.exception("RRF failed")
        fused = bm25_results[:10] if bm25_results else []

    # -- STEP 6: Test Cross-Encoder Reranking --------------------------------─
    print_section("STEP 6: Cross-Encoder Reranking")
    print("  (First run downloads the Cross-Encoder model ~67MB...)")
    t6 = time.time()
    try:
        from app.rag.reranker import CrossEncoderReranker
        reranker = CrossEncoderReranker()
        reranked = reranker.rerank(query=query, candidates=fused, top_k=5)

        print(f"  [OK] Reranker returned {len(reranked)} results ({time.time()-t6:.2f}s)")
        for rank, ev in enumerate(reranked, 1):
            text_preview = ev["text"][:80] + "..." if len(ev["text"]) > 80 else ev["text"]
            print(f"    Rank {rank}: score={ev['score']:.4f}  [{ev['source']}]  {text_preview}")

    except Exception as e:
        print(f"  [FAIL] Cross-Encoder reranking FAILED: {e}")
        logger.exception("Reranker failed")

    # -- STEP 7: Full End-to-End Pipeline ------------------------------------─
    print_section("STEP 7: Full smartverify_rag() Pipeline (End-to-End)")
    t7 = time.time()
    try:
        from app.rag.pipeline import smartverify_rag
        result = smartverify_rag(
            application_id=application_id,
            query=query,
            db=db,
            top_k=5,
        )

        elapsed = time.time() - t7
        print(f"  [OK] Pipeline completed in {elapsed:.2f}s")
        print(f"\n  APPLICATION ID   : {result['application_id']}")
        print(f"  QUERY            : {result['query']}")
        print(f"  CHUNKS INDEXED   : {result['total_chunks_indexed']}")
        print(f"  EVIDENCE RETURNED: {len(result['evidence'])}")
        print_evidence(result["evidence"])

    except Exception as e:
        print(f"  [FAIL] smartverify_rag() FAILED: {e}")
        logger.exception("smartverify_rag failed")

    # -- STEP 8: Batch Pipeline with Multiple Queries --------------------------
    print_section("STEP 8: Batch RAG — 5 Standard Queries")
    t8 = time.time()
    standard_queries = [
        "What is the applicant's income?",
        "Is KYC verified?",
        "What is the requested loan amount and type?",
        "What is the property or vehicle verification status?",
        "What information supports this loan application?",
    ]
    try:
        from app.rag.pipeline import batch_smartverify_rag
        batch_results = batch_smartverify_rag(
            application_id=application_id,
            queries=standard_queries,
            db=db,
            top_k=2,
        )

        print(f"  [OK] Batch pipeline completed in {time.time()-t8:.2f}s")
        for qresult in batch_results:
            print(f"\n  Q: \"{qresult['query']}\"")
            if qresult["evidence"]:
                best = qresult["evidence"][0]
                text_preview = best["text"][:100] + "..." if len(best["text"]) > 100 else best["text"]
                print(f"     Best evidence (score={best['score']:.4f}): {text_preview}")
            else:
                print("     No evidence found.")

    except Exception as e:
        print(f"  [FAIL] Batch pipeline FAILED: {e}")
        logger.exception("Batch pipeline failed")

    # -- Summary --------------------------------------------------------------─
    print_header("[PASS] All Tests Completed")
    print("""
  ARCHITECTURE SUMMARY:
  +--------------------------------------------------------+
  |  User Query  ->  Database (PostgreSQL)                 |
  |             ->  Document Builder (text chunks)         |
  |             ->  BM25 (keyword) + FAISS (semantic)      |
  |             ->  RRF Fusion (combined ranking)          |
  |             ->  Cross-Encoder Reranker (precision)     |
  |             ->  Evidence JSON  <-- NOT a decision maker|
  +--------------------------------------------------------+

  The RAG module provides EVIDENCE to:
    -> VerificationEngine (rule checks)
    -> FraudDetector (risk analysis)
    -> DecisionEngine (final approve/reject)
    """)

    db.close()


# -- Entry Point --------------------------------------------------------------─

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test the SmartVerify Hybrid RAG + Reranking Pipeline"
    )
    parser.add_argument(
        "--app-id",
        type=int,
        default=1,
        help="Application ID from the 'applications' table (default: 1)"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="What is the applicant's income?",
        help="Natural language query to test (default: 'What is the applicant's income?')"
    )
    args = parser.parse_args()

    run_tests(application_id=args.app_id, query=args.query)

