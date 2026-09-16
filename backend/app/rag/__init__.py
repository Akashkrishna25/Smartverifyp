"""
SmartVerify -- Hybrid RAG + Reranking Module
============================================
This package implements the evidence retrieval pipeline:

    fetch_loan_data  ->  DocumentBuilder  ->  BM25 + FAISS
    ->  RRF Fusion  ->  Cross-Encoder Reranker  ->  Evidence JSON

IMPORTANT: This module is a READ-ONLY evidence layer.
It does NOT approve or reject loan applications.
That responsibility belongs to VerificationEngine and DecisionEngine.
"""
