"""
MADL Integration Service - Direct Qdrant Integration
Handles all interactions with Qdrant vector database for method search and storage.
Supports both local and cloud-hosted Qdrant instances.
"""
import asyncio
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

import utils
import config



# Initialize embedding model
embedding_model = None


@dataclass
class ReusableMethod:
    """Represents a reusable method from MADL"""
    method_name: str
    class_name: str
    file_path: str
    intent: str
    semantic_description: str
    keywords: List[str]
    parameters: str
    return_type: str
    full_signature: str
    example: str
    match_score: float
    match_percentage: float


class MADLQdrantClient:
    """Direct Qdrant client for MADL vector database operations - Cloud & Local support"""
    
    def __init__(self):
        self.client = None
        self.is_healthy = False
        self.collection_name = config.QDRANT_COLLECTION_NAME
        self.vector_size = config.QDRANT_VECTOR_SIZE
        self.similarity_threshold = config.QDRANT_SIMILARITY_THRESHOLD
        utils.logger.info(f"[MADL] Initializing Qdrant client for collection: {self.collection_name}")
    
    async def initialize(self):
        """Initialize Qdrant async client - supports cloud and local"""
        try:
            utils.logger.info(f"[MADL] Qdrant Config - Host: {config.QDRANT_HOST}, Port: {config.QDRANT_PORT}, HTTPS: {config.QDRANT_USE_HTTPS}")
            
            self.client = AsyncQdrantClient(
                url=config.MADL_QDRANT_URL,
                api_key=config.QDRANT_API_KEY,
                timeout=30
            )
            
            utils.logger.info(f"[MADL] Connected to Qdrant at {config.MADL_QDRANT_URL}")
            
            # Test connection and ensure collection exists
            await self._ensure_collection_exists()
            self.is_healthy = True
            utils.logger.info("[MADL] Qdrant client initialized successfully")
            return True
        
        except Exception as e:
            self.is_healthy = False
            utils.logger.error(f"[MADL] Failed to initialize Qdrant client: {str(e)}")
            return False
    
    async def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            collections = await self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                utils.logger.info(f"[MADL] Created collection: {self.collection_name}")
            else:
                utils.logger.info(f"[MADL] Collection {self.collection_name} already exists")
        
        except Exception as e:
            utils.logger.error(f"[MADL] Error ensuring collection: {str(e)}")
            raise
    
    async def check_health(self) -> bool:
        """Check if Qdrant service is available"""
        try:
            if not self.client:
                return False
            
            await self.client.get_collections()
            self.is_healthy = True
            return True
        
        except Exception as e:
            self.is_healthy = False
            utils.logger.error(f"[MADL] Health check failed: {str(e)}")
            return False
    
    async def search_reusable_methods(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 5,
        min_score: float = 0.6
    ) -> List[ReusableMethod]:
        """
        Search for reusable methods in Qdrant vector database
        
        Args:
            query: Natural language search query (for logging)
            query_embedding: Query vector embedding
            top_k: Number of results to return
            min_score: Minimum similarity threshold
        
        Returns:
            List of ReusableMethod objects ranked by relevance
        """
        if not self.is_healthy or not self.client:
            utils.logger.warning("[MADL] Qdrant client not healthy, skipping search")
            return []
        
        try:
            utils.logger.debug(f"[MADL] Searching for: {query}")
            
            search_result = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=min_score
            )
            
            results = []
            for point in search_result:
                payload = point.payload
                match_percentage = min(100.0, point.score * 100)
                
                results.append(ReusableMethod(
                    method_name=payload.get("method_name", ""),
                    class_name=payload.get("class_name", ""),
                    file_path=payload.get("file_path", ""),
                    intent=payload.get("intent", ""),
                    semantic_description=payload.get("semantic_description", ""),
                    keywords=payload.get("keywords", []),
                    parameters=payload.get("parameters", ""),
                    return_type=payload.get("return_type", ""),
                    full_signature=payload.get("full_signature", ""),
                    example=payload.get("example", ""),
                    match_score=point.score,
                    match_percentage=match_percentage
                ))
            
            utils.logger.info(f"[MADL] Found {len(results)} reusable methods for query: {query}")
            return results
        
        except Exception as e:
            utils.logger.error(f"[MADL] Search error: {str(e)}")
            return []
    
    async def store_method(
        self,
        method_embedding: List[float],
        method_name: str,
        class_name: str,
        file_path: str,
        intent: str,
        semantic_description: str,
        keywords: List[str],
        parameters: str,
        return_type: str,
        full_signature: str,
        example: str,
        method_code: Optional[str] = None
    ) -> bool:
        """Store a new reusable method in Qdrant vector database"""
        if not self.is_healthy or not self.client:
            utils.logger.warning("[MADL] Qdrant client not healthy, cannot store method")
            return False
        
        try:
            point_id = int(uuid.uuid4().int) % (2**63 - 1)  # Valid Qdrant point ID
            
            payload = {
                "method_name": method_name,
                "class_name": class_name,
                "file_path": file_path,
                "intent": intent,
                "semantic_description": semantic_description,
                "keywords": keywords,
                "parameters": parameters,
                "return_type": return_type,
                "full_signature": full_signature,
                "example": example,
                "method_code": method_code or "",
                "stored_at": datetime.utcnow().isoformat()
            }
            
            point = PointStruct(
                id=point_id,
                vector=method_embedding,
                payload=payload
            )
            
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            utils.logger.info(f"[MADL] Stored method: {class_name}.{method_name}")
            return True
        
        except Exception as e:
            utils.logger.error(f"[MADL] Store error: {str(e)}")
            return False


# Global client instance
madl_qdrant_client = MADLQdrantClient()
madl_client = madl_qdrant_client


async def initialize_madl():
    """Initialize MADL and embedding model on startup"""
    global embedding_model, madl_qdrant_client
    
    try:
        if not config.MADL_ENABLED:
            utils.logger.info("[MADL] MADL is disabled")
            return False
        
        success = await madl_qdrant_client.initialize()
        
        if not success:
            utils.logger.warning("[MADL] Failed to initialize Qdrant, MADL features will be unavailable")
            return False
        
        # Initialize embedding model
        try:
            embedding_model = SentenceTransformer(config.MADL_EMBEDDING_MODEL)
            utils.logger.info(f"[MADL] Embedding model '{config.MADL_EMBEDDING_MODEL}' loaded successfully")
        except Exception as e:
            utils.logger.error(f"[MADL] Failed to load embedding model: {str(e)}")
            embedding_model = None
            return False
        
        utils.logger.info("[MADL] Initialization complete - ready to use cloud Qdrant")
        return True
    
    except Exception as e:
        utils.logger.error(f"[MADL] Initialization error: {str(e)}")
        return False


async def get_query_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding for query text using configured model"""
    global embedding_model
    
    if not embedding_model:
        utils.logger.error("[MADL] Embedding model not available")
        return None
    
    try:
        embedding = embedding_model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    except Exception as e:
        utils.logger.error(f"[MADL] Embedding error: {str(e)}")
        return None


async def search_for_reusable_methods(test_plan: Dict[str, Any]) -> List[ReusableMethod]:
    """
    Search MADL for methods relevant to test plan
    Converts test plan into search queries and finds reusable methods
    """
    global madl_qdrant_client, embedding_model
    
    if not madl_qdrant_client.is_healthy or not embedding_model:
        utils.logger.debug("[MADL] MADL not available, skipping search")
        return []
    
    try:
        search_queries = []
        
        current_steps = test_plan.get("current_bdd_steps", {})
        if isinstance(current_steps, dict):
            for step, args in current_steps.items():
                search_query = f"{step} with {args}" if args else step
                search_queries.append(search_query)
        
        if not search_queries:
            utils.logger.debug("[MADL] No steps found in test plan")
            return []
        
        all_methods = []
        for query in search_queries:
            try:
                query_embedding = await get_query_embedding(query)
                if not query_embedding:
                    continue
                
                methods = await madl_qdrant_client.search_reusable_methods(
                    query=query,
                    query_embedding=query_embedding,
                    top_k=5,
                    min_score=0.6
                )
                all_methods.extend(methods)
            
            except Exception as e:
                utils.logger.error(f"[MADL] Error searching for query '{query}': {str(e)}")
                continue
        
        # Deduplicate by method signature
        unique_methods = {}
        for method in all_methods:
            key = f"{method.class_name}.{method.method_name}"
            if key not in unique_methods or method.match_score > unique_methods[key].match_score:
                unique_methods[key] = method
        
        result = list(unique_methods.values())
        utils.logger.info(f"[MADL] Found {len(result)} unique reusable methods")
        return result
    
    except Exception as e:
        utils.logger.error(f"[MADL] Search error: {str(e)}")
        return []
