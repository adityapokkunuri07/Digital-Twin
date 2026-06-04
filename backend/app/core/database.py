from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
import logging

logger = logging.getLogger(__name__)

class DatabaseService(ABC):
    @abstractmethod
    async def save_expert_config(
        self, config_id: UUID, doctor_id: UUID, workflow_config: Dict[str, Any], 
        active_version: str, is_feasible: bool, validation_errors: List[str]
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_expert_config(self, config_id: UUID) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def save_cot_nodes(self, config_id: UUID, nodes: List[Dict[str, Any]]) -> None:
        pass

    @abstractmethod
    async def save_cot_edges(self, config_id: UUID, edges: List[Dict[str, Any]]) -> None:
        pass

    @abstractmethod
    async def get_cot_nodes(self, config_id: UUID) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_cot_edges(self, config_id: UUID) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def delete_knowledge_chunks(self, config_id: UUID) -> None:
        pass

    @abstractmethod
    async def save_knowledge_chunks(self, config_id: UUID, chunks: List[Dict[str, Any]]) -> None:
        pass

    @abstractmethod
    async def match_knowledge_chunks(self, embedding: List[float], threshold: float, limit: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def match_knowledge_chunks_lexical(self, query_text: str, threshold: float, limit: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_knowledge_chunk_by_path(self, config_id: UUID, parent_path: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_active_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def save_active_session(
        self, session_id: UUID, conversation_id: UUID, config_id: UUID, 
        current_node: str, graph_state: Dict[str, Any], is_paused: bool, requires_review: bool
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def create_execution_trace(
        self, session_id: UUID, step_name: str, prompt_used: str, 
        response_generated: str, retrieved_chunk_ids: List[UUID], classification_score: float
    ) -> Dict[str, Any]:
        pass


class SupabaseDatabaseService(DatabaseService):
    def __init__(self, url: str = "", key: str = ""):
        self.url = url
        self.key = key
        self.client = None
        self.use_mock = True

        if url and key:
            try:
                from supabase import create_client
                self.client = create_client(url, key)
                self.use_mock = False
                logger.info("Supabase client initialized successfully.")
            except ImportError:
                logger.warning("Supabase package not installed. Falling back to mock database.")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {e}. Falling back to mock database.")

        if self.use_mock:
            # Memory DB structures for mock/offline fallback execution
            self._configs: Dict[str, Dict[str, Any]] = {}
            self._cot_nodes: Dict[str, List[Dict[str, Any]]] = {}
            self._cot_edges: Dict[str, List[Dict[str, Any]]] = {}
            self._knowledge_chunks: Dict[str, List[Dict[str, Any]]] = {}
            self._sessions: Dict[str, Dict[str, Any]] = {}
            self._traces: List[Dict[str, Any]] = []
            logger.info("Running in Mock Database mode.")

    async def save_expert_config(
        self, config_id: UUID, doctor_id: UUID, workflow_config: Dict[str, Any], 
        active_version: str, is_feasible: bool, validation_errors: List[str]
    ) -> Dict[str, Any]:
        cid_str = str(config_id)
        did_str = str(doctor_id)
        record = {
            "config_id": cid_str,
            "doctor_id": did_str,
            "workflow_config": workflow_config,
            "active_version": active_version,
            "is_feasible": is_feasible,
            "validation_errors": validation_errors,
        }
        if self.use_mock:
            self._configs[cid_str] = record
            return record
        
        # Real Supabase upsert
        res = self.client.table("expert_twin_configs").upsert(record).execute()
        return res.data[0] if res.data else record

    async def get_expert_config(self, config_id: UUID) -> Optional[Dict[str, Any]]:
        cid_str = str(config_id)
        if self.use_mock:
            return self._configs.get(cid_str)
        res = self.client.table("expert_twin_configs").select("*").eq("config_id", cid_str).execute()
        return res.data[0] if res.data else None

    async def save_cot_nodes(self, config_id: UUID, nodes: List[Dict[str, Any]]) -> None:
        cid_str = str(config_id)
        formatted_nodes = []
        for node in nodes:
            formatted_nodes.append({
                "node_id": str(node.get("node_id", uuid4())),
                "config_id": cid_str,
                "title": node.get("title", ""),
                "node_type": node.get("node_type", "intake"),
                "content": node.get("content", ""),
                "metadata": node.get("metadata", {})
            })
            
        if self.use_mock:
            self._cot_nodes[cid_str] = formatted_nodes
            return
        
        if formatted_nodes:
            self.client.table("cot_nodes").upsert(formatted_nodes).execute()

    async def save_cot_edges(self, config_id: UUID, edges: List[Dict[str, Any]]) -> None:
        cid_str = str(config_id)
        formatted_edges = []
        for edge in edges:
            formatted_edges.append({
                "edge_id": str(edge.get("edge_id", uuid4())),
                "config_id": cid_str,
                "source_node_id": str(edge["source_node_id"]),
                "target_node_id": str(edge["target_node_id"]),
                "relationship_type": edge.get("relationship_type", "related_to")
            })
            
        if self.use_mock:
            self._cot_edges[cid_str] = formatted_edges
            return
        
        if formatted_edges:
            self.client.table("cot_edges").upsert(formatted_edges).execute()

    async def get_cot_nodes(self, config_id: UUID) -> List[Dict[str, Any]]:
        cid_str = str(config_id)
        if self.use_mock:
            return self._cot_nodes.get(cid_str, [])
        res = self.client.table("cot_nodes").select("*").eq("config_id", cid_str).execute()
        return res.data if res.data else []

    async def get_cot_edges(self, config_id: UUID) -> List[Dict[str, Any]]:
        cid_str = str(config_id)
        if self.use_mock:
            return self._cot_edges.get(cid_str, [])
        res = self.client.table("cot_edges").select("*").eq("config_id", cid_str).execute()
        return res.data if res.data else []

    async def delete_knowledge_chunks(self, config_id: UUID) -> None:
        cid_str = str(config_id)
        if self.use_mock:
            self._knowledge_chunks[cid_str] = []
            return
        self.client.table("knowledge_chunks").delete().eq("config_id", cid_str).execute()

    async def save_knowledge_chunks(self, config_id: UUID, chunks: List[Dict[str, Any]]) -> None:
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
                "metadata": metadata
            })
            
        if self.use_mock:
            self._knowledge_chunks[cid_str] = formatted_chunks
            return
        
        if formatted_chunks:
            self.client.table("knowledge_chunks").insert(formatted_chunks).execute()

    async def match_knowledge_chunks(self, embedding: List[float], threshold: float, limit: int) -> List[Dict[str, Any]]:
        if self.use_mock:
            # simple mock cosine similarity simulation
            # returns all stored chunks as if they matched for testing
            all_chunks = []
            for config_chunks in self._knowledge_chunks.values():
                for c in config_chunks:
                    c_copy = c.copy()
                    c_copy["similarity"] = 0.90 # default mocked score above threshold
                    all_chunks.append(c_copy)
            # sort by order index or path
            return all_chunks[:limit]

        # Call the Supabase pgvector match function (which would be defined in SQL as HNSW similarity search)
        res = self.client.rpc("match_knowledge_chunks", {
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": limit
        }).execute()
        return res.data if res.data else []

    async def match_knowledge_chunks_lexical(self, query_text: str, threshold: float, limit: int) -> List[Dict[str, Any]]:
        if self.use_mock:
            # Mock trigram search simulation: filters if words in query exist in chunk content
            matches = []
            words = set(query_text.lower().split())
            for config_chunks in self._knowledge_chunks.values():
                for c in config_chunks:
                    c_words = set(c["content"].lower().split())
                    common = words.intersection(c_words)
                    score = len(common) / max(len(words), 1)
                    if score > threshold or query_text.lower() in c["content"].lower():
                        c_copy = c.copy()
                        c_copy["lexical_score"] = max(score, 0.88)
                        matches.append(c_copy)
            return sorted(matches, key=lambda x: x.get("lexical_score", 0), reverse=True)[:limit]

        res = self.client.rpc("match_knowledge_chunks_lexical", {
            "query_text": query_text,
            "match_threshold": threshold,
            "match_limit": limit
        }).execute()
        return res.data if res.data else []

    async def get_knowledge_chunk_by_path(self, config_id: UUID, parent_path: str) -> Optional[Dict[str, Any]]:
        cid_str = str(config_id)
        if self.use_mock:
            for c in self._knowledge_chunks.get(cid_str, []):
                if c.get("metadata", {}).get("current_path") == parent_path or c.get("current_path") == parent_path:
                    return c
            return None
        res = self.client.table("knowledge_chunks").select("*").eq("config_id", cid_str).eq("metadata->>current_path", parent_path).execute()
        return res.data[0] if res.data else None

    async def get_active_session(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        sid_str = str(session_id)
        if self.use_mock:
            return self._sessions.get(sid_str)
        res = self.client.table("active_sessions").select("*").eq("session_id", sid_str).execute()
        return res.data[0] if res.data else None

    async def save_active_session(
        self, session_id: UUID, conversation_id: UUID, config_id: UUID, 
        current_node: str, graph_state: Dict[str, Any], is_paused: bool, requires_review: bool
    ) -> Dict[str, Any]:
        sid_str = str(session_id)
        record = {
            "session_id": sid_str,
            "conversation_id": str(conversation_id),
            "config_id": str(config_id),
            "current_node": current_node,
            "graph_state": graph_state,
            "is_paused": is_paused,
            "requires_review": requires_review,
        }
        if self.use_mock:
            self._sessions[sid_str] = record
            return record
        
        res = self.client.table("active_sessions").upsert(record).execute()
        return res.data[0] if res.data else record

    async def create_execution_trace(
        self, session_id: UUID, step_name: str, prompt_used: str, 
        response_generated: str, retrieved_chunk_ids: List[UUID], classification_score: float
    ) -> Dict[str, Any]:
        record = {
            "trace_id": str(uuid4()),
            "session_id": str(session_id),
            "step_name": step_name,
            "prompt_used": prompt_used,
            "response_generated": response_generated,
            "retrieved_chunk_ids": [str(x) for x in retrieved_chunk_ids],
            "classification_score": classification_score,
        }
        if self.use_mock:
            self._traces.append(record)
            return record
        
        res = self.client.table("execution_traces").insert(record).execute()
        return res.data[0] if res.data else record
