"""
MADL Module - vector DB (Qdrant) + step-embedding support

Purpose:
- Provide search/store APIs for reusable methods extracted from successful executions
- Store step-level embeddings (test step -> code snippet) so we can reuse code pieces mapped to steps
- Keep payload minimal per project rules (no language, no filepath/version/stored dates)
"""

import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, PointStruct, Distance
from sentence_transformers import SentenceTransformer

from app import utils
from app import config

# dataclass used by callers
@dataclass
class ReusableMethod:
    method_name: str
    class_name: str
    intent: str
    semantic_description: str
    keywords: List[str]
    parameters: Optional[str]
    return_type: Optional[str]
    full_signature: str
    example: Optional[str]
    method_code: str
    match_score: float
    match_percentage: float

# dataclass for step snippet
@dataclass
class StepSnippet:
    testcaseid: str
    step_text: str
    snippet_code: str
    snippet_id: str

class MADLModule:
    def __init__(self):
        self.client: Optional[AsyncQdrantClient] = None
        self.collection_name = config.QDRANT_COLLECTION_NAME
        self.vector_size = config.QDRANT_VECTOR_SIZE
        self.similarity_threshold = getattr(config, "QDRANT_SIMILARITY_THRESHOLD", 0.55)
        self.embedding_model_name = getattr(config, "MADL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.embedding_model: Optional[SentenceTransformer] = None
        self.is_ready = False

    async def initialize(self) -> bool:
        """Initialize Qdrant client and embedding model."""
        try:
            utils.logger.info(f"[MADL] initialize: connecting to {config.MADL_QDRANT_URL}")
            self.client = AsyncQdrantClient(url=config.MADL_QDRANT_URL, api_key=getattr(config, "QDRANT_API_KEY", None))
            await self._ensure_collection()
            # load embedding model
            try:
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                utils.logger.info(f"[MADL] loaded embedding model {self.embedding_model_name}")
            except Exception as e:
                utils.logger.error(f"[MADL] failed to load embedding model: {e}")
                self.embedding_model = None
                return False

            self.is_ready = True
            utils.logger.info("[MADL] initialization complete")
            return True
        except Exception as e:
            utils.logger.error(f"[MADL] initialization error: {e}")
            self.is_ready = False
            return False

    async def _ensure_collection(self):
        """Create collection if missing."""
        try:
            collections = await self.client.get_collections()
            existing = [c.name for c in collections.collections]
            if self.collection_name not in existing:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )
                utils.logger.info(f"[MADL] created collection {self.collection_name}")
            else:
                utils.logger.debug(f"[MADL] collection {self.collection_name} exists")
        except Exception as e:
            utils.logger.error(f"[MADL] ensure_collection error: {e}")
            raise

    async def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """Return embedding vector for given text (uses sentence-transformers)."""
        if not self.embedding_model:
            utils.logger.error("[MADL] embedding model not loaded")
            return None
        try:
            vec = self.embedding_model.encode(text, convert_to_tensor=False)
            return vec.tolist()
        except Exception as e:
            utils.logger.error(f"[MADL] embedding error: {e}")
            return None

    async def store_reusable_method(
        self,
        method_name: str,
        class_name: str,
        intent: str,
        semantic_description: str,
        keywords: List[str],
        parameters: Optional[str],
        return_type: Optional[str],
        full_signature: str,
        example: Optional[str],
        method_code: str
    ) -> bool:
        """
        Store a reusable method in vector DB.

        IMPORTANT: payload intentionally excludes 'language', 'filepath', 'version', 'stored/updated dates'.
        Those fields were removed per project requirement.
        """
        if not self.is_ready:
            utils.logger.warning("[MADL] not initialized, cannot store method")
            return False

        try:
            # Build canonical text to embed
            embed_text = " ".join(filter(None, [
                full_signature,
                intent,
                semantic_description,
                " ".join(keywords or []),
                str(parameters or ""),
                str(return_type or ""),
                example or ""
            ]))
            vec = await self.get_text_embedding(embed_text)
            if not vec:
                utils.logger.error("[MADL] failed to compute embedding for method")
                return False

            # create payload
            payload = {
                "method_name": method_name,
                "class_name": class_name,
                "intent": intent,
                "semantic_description": semantic_description,
                "keywords": keywords,
                "parameters": parameters or "",
                "return_type": return_type or "",
                "full_signature": full_signature,
                "example": example or "",
                "method_code": method_code or ""
            }

            point_id = int(uuid.uuid4().int) % (2**63 - 1)
            point = PointStruct(id=point_id, vector=vec, payload=payload)
            await self.client.upsert(collection_name=self.collection_name, points=[point])
            utils.logger.info(f"[MADL] stored method {full_signature} (id={point_id})")
            return True
        except Exception as e:
            utils.logger.error(f"[MADL] store_reusable_method error: {e}")
            return False

    async def search_reusable_methods_for_testplan(self, testplan: Dict[str, Any], top_k: int = 8) -> List[ReusableMethod]:
        """
        Given a testplan dict, produce search queries (per step + aggregated context),
        compute embeddings and search Qdrant. Returns deduplicated ReusableMethod list.
        """
        if not self.is_ready:
            utils.logger.debug("[MADL] not ready for search")
            return []

        try:
            # Build queries from steps
            queries = []
            # support both legacy keys
            current_steps = testplan.get("current_bdd_steps") or testplan.get("current - bdd steps") or {}
            if isinstance(current_steps, dict):
                for step, args in current_steps.items():
                    if args:
                        queries.append(f"{step} {json.dumps(args)}")
                    else:
                        queries.append(step)

            # also include aggregated testplan text as fallback
            queries.append(json.dumps(testplan))

            all_candidates = []
            for q in queries:
                emb = await self.get_text_embedding(q)
                if not emb:
                    continue
                hits = await self.client.search(collection_name=self.collection_name, query_vector=emb, limit=top_k, score_threshold=self.similarity_threshold)
                for p in hits:
                    payload = p.payload or {}
                    match_pct = min(100.0, (p.score or 0.0) * 100.0)
                    candidate = ReusableMethod(
                        method_name=payload.get("method_name", ""),
                        class_name=payload.get("class_name", ""),
                        intent=payload.get("intent", ""),
                        semantic_description=payload.get("semantic_description", ""),
                        keywords=payload.get("keywords", []),
                        parameters=payload.get("parameters", ""),
                        return_type=payload.get("return_type", ""),
                        full_signature=payload.get("full_signature", ""),
                        example=payload.get("example", ""),
                        method_code=payload.get("method_code", ""),
                        match_score=p.score or 0.0,
                        match_percentage=match_pct
                    )
                    all_candidates.append(candidate)

            # dedupe by signature with best score
            unique = {}
            for c in all_candidates:
                key = f"{c.class_name}.{c.method_name}"
                if key not in unique or c.match_score > unique[key].match_score:
                    unique[key] = c

            results = list(unique.values())
            utils.logger.info(f"[MADL] search found {len(results)} candidates")
            return results
        except Exception as e:
            utils.logger.error(f"[MADL] search_reusable_methods_for_testplan error: {e}")
            return []

    async def store_step_embeddings(self, testcaseid: str, step_mappings: List[Dict[str, str]]) -> bool:
        """
        Store step-level embeddings.

        step_mappings: list of dicts:
          {
            "step_text": "<BDD step text>",
            "snippet_code": "<the code snippet/run-time mapping for this step>"
          }

        Each stored point payload contains: testcaseid, step_text, snippet_code, snippet_id
        """
        if not self.is_ready:
            utils.logger.warning("[MADL] not initialized, cannot store steps")
            return False

        try:
            points = []
            for m in step_mappings:
                step_text = m.get("step_text", "")
                snippet_code = m.get("snippet_code", "")
                canonical = f"{step_text} {snippet_code[:400]}"  # include some code context
                vec = await self.get_text_embedding(canonical)
                if not vec:
                    continue
                snippet_id = str(uuid.uuid4())
                payload = {
                    "type": "step_snippet",
                    "testcaseid": testcaseid,
                    "step_text": step_text,
                    "snippet_code": snippet_code,
                    "snippet_id": snippet_id
                }
                point_id = int(uuid.uuid4().int) % (2**63 - 1)
                points.append(PointStruct(id=point_id, vector=vec, payload=payload))

            if points:
                await self.client.upsert(collection_name=self.collection_name, points=points)
                utils.logger.info(f"[MADL] stored {len(points)} step-snippet points for {testcaseid}")
            return True
        except Exception as e:
            utils.logger.error(f"[MADL] store_step_embeddings error: {e}")
            return False

    async def search_by_step(self, step_text: str, top_k: int = 6) -> List[StepSnippet]:
        """
        Search step-snippets by a step text and return matching snippets.
        """
        if not self.is_ready:
            return []

        try:
            emb = await self.get_text_embedding(step_text)
            if not emb:
                return []
            hits = await self.client.search(collection_name=self.collection_name, query_vector=emb, limit=top_k, score_threshold=self.similarity_threshold)
            snippets = []
            for p in hits:
                payload = p.payload or {}
                if payload.get("type") != "step_snippet":
                    continue
                snippets.append(StepSnippet(
                    testcaseid=payload.get("testcaseid", ""),
                    step_text=payload.get("step_text", ""),
                    snippet_code=payload.get("snippet_code", ""),
                    snippet_id=payload.get("snippet_id", "")
                ))
            utils.logger.info(f"[MADL] search_by_step found {len(snippets)} snippets")
            return snippets
        except Exception as e:
            utils.logger.error(f"[MADL] search_by_step error: {e}")
            return []

# Single global instance for app to import
madl_module = MADLModule()
