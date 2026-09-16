"""
Vector Database Service
Manages ChromaDB collections for policies, rules, and historical applications.
Provides embedding, indexing, and similarity search capabilities.
"""
import logging
import os
import chromadb
from chromadb.config import Settings
from app.core.config import settings

logger = logging.getLogger(__name__)

class VectorService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # Initialize ChromaDB client using the local persistent directory
        db_path = settings.CHROMADB_DIR
        # If running locally without docker, /app/chroma_db might not exist.
        if not db_path.startswith("/") and not db_path.startswith("C:\\"):
             db_path = os.path.join(os.getcwd(), "chroma_db")
        elif db_path == "/app/chroma_db" and not os.path.exists("/app"):
             db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_db")

        os.makedirs(db_path, exist_ok=True)
        try:
            self.client = chromadb.PersistentClient(path=db_path, settings=Settings(anonymized_telemetry=False))
            # Create or get collections
            self.policy_collection = self.client.get_or_create_collection(name="bank_policies")
            self.application_collection = self.client.get_or_create_collection(name="historical_applications")
            logger.info(f"VectorService initialized with ChromaDB at {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None

    def index_policy(self, doc_id: str, text: str, metadata: dict = None):
        """Chunk and embed a policy document into the vector database."""
        if not self.client:
            return False
        
        metadata = metadata or {}
        try:
            self.policy_collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to index policy {doc_id}: {e}")
            return False

    def retrieve_policies(self, query: str, n_results: int = 3) -> list:
        """Retrieve top-k relevant policies based on the query."""
        if not self.client:
            return []
            
        try:
            results = self.policy_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            retrieved = []
            if results and results.get("documents") and len(results["documents"]) > 0:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else [{}] * len(docs)
                for doc, meta in zip(docs, metas):
                    retrieved.append({"text": doc, "metadata": meta})
            return retrieved
        except Exception as e:
            logger.error(f"Failed to retrieve policies for query '{query}': {e}")
            return []

    def store_application_vector(self, app_id: int, extracted_info: dict, fraud_result: dict, verification_score: float, status: str):
        """Embed and store an application's profile and decision for similarity search."""
        if not self.client:
            return False
            
        # Create a document representation of the application
        doc_text = f"Applicant Profile: {extracted_info.get('applicant_name', '')} "
        doc_text += f"Income: {extracted_info.get('monthly_income', '')} "
        doc_text += f"Loan: {extracted_info.get('loan_amount', '')} "
        doc_text += f"Employer: {extracted_info.get('employer_name', '')} "
        doc_text += f"Verification Status: {status} "
        if fraud_result.get('fraud_flag'):
            doc_text += "FLAGGED AS FRAUD. "
            doc_text += " ".join(fraud_result.get('alerts', []))
            
        metadata = {
            "application_id": app_id,
            "status": status,
            "verification_score": verification_score,
            "fraud_score": fraud_result.get("risk_score", 0),
            "fraud_flag": fraud_result.get("fraud_flag", False)
        }
        
        try:
            self.application_collection.add(
                documents=[doc_text],
                metadatas=[metadata],
                ids=[str(app_id)]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store application vector {app_id}: {e}")
            return False

    def find_similar_applications(self, extracted_info: dict, n_results: int = 5) -> list:
        """Retrieve top-K similar applications based on the applicant's profile."""
        if not self.client:
            return []
            
        query_text = f"Applicant Profile: {extracted_info.get('applicant_name', '')} "
        query_text += f"Income: {extracted_info.get('monthly_income', '')} "
        query_text += f"Loan: {extracted_info.get('loan_amount', '')} "
        query_text += f"Employer: {extracted_info.get('employer_name', '')}"
            
        try:
            results = self.application_collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            similar_apps = []
            if results and results.get("documents") and len(results["documents"]) > 0:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else [{}] * len(docs)
                distances = results["distances"][0] if "distances" in results and results["distances"] else [0] * len(docs)
                
                for doc, meta, dist in zip(docs, metas, distances):
                    # Convert distance to a similarity score (0-100)
                    sim_score = max(0, 100 - (dist * 50)) 
                    similar_apps.append({
                        "similarity_score": round(sim_score, 2),
                        "application_id": meta.get("application_id"),
                        "verification_score": meta.get("verification_score"),
                        "fraud_score": meta.get("fraud_score"),
                        "decision": meta.get("status"),
                        "fraud_flag": meta.get("fraud_flag"),
                        "profile_summary": doc
                    })
            return similar_apps
        except Exception as e:
            logger.error(f"Failed to retrieve similar applications: {e}")
            return []
