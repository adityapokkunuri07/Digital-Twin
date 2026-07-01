"""
Supabase Knowledge Repository — KnowledgeRepository implementation.

Handles persistence for knowledge_chunks table including
vector search, lexical search, and materialized path lookups.
Single Responsibility: Only knowledge chunk operations.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
import logging

from backend.app.core.interfaces.repositories import KnowledgeRepository
from backend.app.repositories.base import SupabaseClientMixin

logger = logging.getLogger(__name__)


class SupabaseKnowledgeRepository(SupabaseClientMixin, KnowledgeRepository):
    """
    Concrete implementation of KnowledgeRepository backed by Supabase.
    Falls back to in-memory list store when credentials are unavailable.
    """

    def __init__(self, url: str = "", key: str = ""):
        super().__init__(url, key)
        if self.use_mock:
            self._knowledge_chunks: Dict[str, List[Dict[str, Any]]] = {}

    async def delete_knowledge_chunks(self, config_id: UUID) -> None:
        cid_str = str(config_id)

        if self.use_mock:
            self._knowledge_chunks[cid_str] = []
            return

        self.client.table("knowledge_chunks").delete().eq("config_id", cid_str).execute()

    async def save_knowledge_chunks(
        self, config_id: UUID, chunks: List[Dict[str, Any]]
    ) -> None:
        cid_str = str(config_id)
        formatted_chunks = []

        for chunk in chunks:
            metadata = chunk.get("metadata", {}).copy()
            if "current_path" in chunk:
                metadata["current_path"] = chunk["current_path"]

            formatted_chunks.append({
                "chunk_id": str(chunk.get("chunk_id", uuid4())),
                "config_id": cid_str,
                "order_index": chunk.get("order_index", 0),
                "title": chunk.get("title", ""),
                "content": chunk.get("content", ""),
                "parent_path": chunk.get("parent_path", ""),
                "tags": chunk.get("tags", []),
                "synthetic_questions": chunk.get("synthetic_questions", []),
                "embedding": chunk.get("embedding"),
                "operational_mode": chunk.get("operational_mode", "LEARN"),
                "metadata": metadata,
            })

        if self.use_mock:
            self._knowledge_chunks[cid_str] = formatted_chunks
            return

        if formatted_chunks:
            self.client.table("knowledge_chunks").insert(formatted_chunks).execute()

    async def match_knowledge_chunks(
        self, config_id: UUID, embedding: List[float], threshold: float, limit: int, operational_mode: str = None
    ) -> List[Dict[str, Any]]:
        cid_str = str(config_id)

        if self.use_mock:
            # Per-expert isolation: only return chunks for the requested config_id
            all_chunks = []
            for c in self._knowledge_chunks.get(cid_str, []):
                if operational_mode and c.get("operational_mode", "LEARN") != operational_mode:
                    continue
                c_copy = c.copy()
                c_copy["similarity"] = 0.90  # default mocked score above threshold
                all_chunks.append(c_copy)
            return all_chunks[:limit]

        # Call the Supabase pgvector match function (HNSW similarity search)
        # config_id filter enforces per-expert data isolation at the DB layer
        res = self.client.rpc("match_knowledge_chunks_with_mode", {
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": limit,
            "filter_mode": operational_mode,
            "p_config_id": cid_str,
        }).execute()
        return res.data if res.data else []

    async def match_knowledge_chunks_lexical(
        self, config_id: UUID, query_text: str, threshold: float, limit: int, operational_mode: str = None
    ) -> List[Dict[str, Any]]:
        cid_str = str(config_id)

        if self.use_mock:
            # Per-expert isolation: only search chunks for the requested config_id
            matches = []
            words = set(query_text.lower().split())
            for c in self._knowledge_chunks.get(cid_str, []):
                if operational_mode and c.get("operational_mode", "LEARN") != operational_mode:
                    continue
                c_words = set(c["content"].lower().split())
                common = words.intersection(c_words)
                score = len(common) / max(len(words), 1)
                if score > threshold or query_text.lower() in c["content"].lower():
                    c_copy = c.copy()
                    c_copy["lexical_score"] = max(score, 0.88)
                    matches.append(c_copy)
            return sorted(
                matches, key=lambda x: x.get("lexical_score", 0), reverse=True
            )[:limit]

        # config_id filter enforces per-expert data isolation at the DB layer
        res = self.client.rpc("match_knowledge_chunks_lexical_with_mode", {
            "query_text": query_text,
            "match_threshold": threshold,
            "match_limit": limit,
            "filter_mode": operational_mode,
            "p_config_id": cid_str,
        }).execute()
        return res.data if res.data else []

    async def get_knowledge_chunk_by_path(
        self, config_id: UUID, parent_path: str
    ) -> Optional[Dict[str, Any]]:
        cid_str = str(config_id)

        if self.use_mock:
            for c in self._knowledge_chunks.get(cid_str, []):
                if (
                    c.get("metadata", {}).get("current_path") == parent_path
                    or c.get("current_path") == parent_path
                ):
                    return c
            return None

        res = (
            self.client.table("knowledge_chunks")
            .select("*")
            .eq("config_id", cid_str)
            .eq("metadata->>current_path", parent_path)
            .execute()
        )
        return res.data[0] if res.data else None
