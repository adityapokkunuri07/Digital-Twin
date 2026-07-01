import asyncio
from typing import List, Dict, Any, Tuple
from uuid import UUID
import logging
from backend.app.core.interfaces.repositories import KnowledgeRepository
from backend.app.core.interfaces.embedding import EmbeddingService

logger = logging.getLogger(__name__)

class HybridRAGEngine:
    def __init__(self, db: KnowledgeRepository, embedding_service: EmbeddingService):
        self.db = db
        self.embedding_service = embedding_service
        self.vector_weight = 0.7
        self.lexical_weight = 0.3
        self.confidence_gate = 0.85

    async def retrieve_context(
        self, config_id: UUID, query_text: str, limit: int = 5, operational_mode: str = None
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Retrieves hydrated and deduplicated parent context based on query text.
        Returns:
            Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]: 
                - String representation of the hydrated context
                - List of selected raw chunks before hydration
                - List of all rejected chunks below the confidence gate
        """
        # 1. Generate query embedding
        query_embedding = self.embedding_service.get_embedding(query_text)

        # 2. Run multi-lane search in parallel (scoped by config_id for per-expert isolation)
        # Lane A: Vector search (HNSW cosine similarity)
        # Lane B: Lexical search (trigram matching)
        vector_task = self.db.match_knowledge_chunks(config_id, query_embedding, threshold=0.0, limit=20, operational_mode=operational_mode)
        lexical_task = self.db.match_knowledge_chunks_lexical(config_id, query_text, threshold=0.0, limit=20, operational_mode=operational_mode)
        
        vector_results, lexical_results = await asyncio.gather(vector_task, lexical_task)

        # 3. Score Fusion
        # Create map of chunk_id -> (chunk, vector_score, lexical_score)
        fusion_map: Dict[str, Tuple[Dict[str, Any], float, float]] = {}

        for vr in vector_results:
            cid = vr["chunk_id"]
            score = vr.get("similarity", 0.0)
            fusion_map[cid] = (vr, score, 0.0)

        for lr in lexical_results:
            cid = lr["chunk_id"]
            score = lr.get("lexical_score", 0.0)
            if cid in fusion_map:
                chunk, v_score, _ = fusion_map[cid]
                fusion_map[cid] = (chunk, v_score, score)
            else:
                fusion_map[cid] = (lr, 0.0, score)

        # Compute combined score
        scored_chunks = []
        for cid, (chunk, v_score, l_score) in fusion_map.items():
            # If a chunk matched on both lanes, combine. Else weight individual lanes.
            combined_score = (self.vector_weight * v_score) + (self.lexical_weight * l_score)
            
            chunk_copy = chunk.copy()
            chunk_copy["vector_score"] = v_score
            chunk_copy["lexical_score"] = l_score
            chunk_copy["combined_score"] = combined_score
            scored_chunks.append(chunk_copy)

        # Sort by combined score descending
        scored_chunks.sort(key=lambda x: x["combined_score"], reverse=True)

        # 4. Zero-Trust Gate Filter (threshold > 0.85)
        accepted_chunks = []
        rejected_chunks = []

        for sc in scored_chunks:
            if sc["combined_score"] > self.confidence_gate:
                accepted_chunks.append(sc)
            else:
                rejected_chunks.append(sc)

        # Limit accepted candidates
        selected_candidates = accepted_chunks[:limit]

        # 5. Recursive Parent Hydration & Deduplication
        hydrated_contexts = []
        hydrated_paths = set()

        for cand in selected_candidates:
            parent_path = cand.get("parent_path", "")
            current_path = cand.get("current_path", "")
            
            # Use current path if it's already a parent node (e.g. root node),
            # otherwise seek to hydrate its parent section
            target_path = parent_path if parent_path else current_path
            
            if not target_path:
                # No path mapping, just use candidate directly
                hydrated_contexts.append(f"Title: {cand['title']}\nContent: {cand['content']}")
                continue
                
            if target_path in hydrated_paths:
                # Already hydrated this section, skip to deduplicate
                continue

            # Retrieve the full parent block using the path
            parent_chunk = await self.db.get_knowledge_chunk_by_path(config_id, target_path)
            
            if parent_chunk:
                hydrated_paths.add(target_path)
                context_str = f"=== Section: {parent_chunk['title']} ({target_path}) ===\n{parent_chunk['content']}\n"
                # Append child text if not already contained within parent
                if cand["content"] not in parent_chunk["content"]:
                    context_str += f"Detail ({cand['title']}): {cand['content']}\n"
                hydrated_contexts.append(context_str)
            else:
                # Fallback to current candidate if parent lookup fails
                hydrated_paths.add(current_path)
                hydrated_contexts.append(f"=== Detail: {cand['title']} ({current_path}) ===\n{cand['content']}")

        # Merge contexts into a single block
        final_context_block = "\n".join(hydrated_contexts) if hydrated_contexts else "No authoritative matching context found."

        return final_context_block, selected_candidates, rejected_chunks
