import re
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from backend.app.core.interfaces.repositories import KnowledgeRepository
from backend.app.core.interfaces.embedding import EmbeddingService

class StructuralRAGIngestionPipeline:
    def __init__(self, db: KnowledgeRepository, embedding_service: EmbeddingService):
        self.db = db
        self.embedding_service = embedding_service
        # Synonym normalization mappings
        self.synonym_map = {
            "intro": "overview",
            "introduction": "overview",
            "scope": "overview",
            "background": "overview",
            "triage": "intake",
            "assessment": "evaluation",
            "treatment": "action",
            "intervention": "action"
        }

    def _normalize_title(self, title: str) -> str:
        # Lowercase, replace non-alphanumeric with underscore
        normalized = title.strip().lower()
        normalized = re.sub(r'[^a-z0-9\s-]', '', normalized)
        normalized = re.sub(r'[\s-]+', '_', normalized)
        
        # Apply synonym normalization
        parts = normalized.split("_")
        normalized_parts = [self.synonym_map.get(p, p) for p in parts]
        return "_".join(normalized_parts)

    def parse_document(self, raw_text: str) -> List[Dict[str, Any]]:
        """
        Stage A: Deterministic Skeleton Construction
        Parses raw markdown text into layout blocks with heading paths, tracking stacks,
        and filling gaps with virtual parent nodes.
        """
        lines = raw_text.splitlines()
        chunks = []
        
        active_stack = []
        current_chunk = None
        order_index = 0
        
        # Track seen paths to detect gap-filling needs
        seen_paths = set()

        def save_current_chunk():
            nonlocal current_chunk
            if current_chunk and current_chunk["content"].strip():
                chunks.append(current_chunk)

        for line in lines:
            h1_match = re.match(r'^#\s+(.+)$', line)
            h2_match = re.match(r'^##\s+(.+)$', line)
            h3_match = re.match(r'^###\s+(.+)$', line)

            if h1_match:
                save_current_chunk()
                title = h1_match.group(1).strip()
                norm_title = self._normalize_title(title)
                active_stack = [norm_title]
                
                path = norm_title
                seen_paths.add(path)
                
                current_chunk = {
                    "order_index": order_index,
                    "title": title,
                    "content": "",
                    "parent_path": "", # Root level has no parent path
                    "current_path": path
                }
                order_index += 1

            elif h2_match:
                save_current_chunk()
                title = h2_match.group(1).strip()
                norm_title = self._normalize_title(title)
                
                # Check for gap: if H1 is missing, inject virtual H1
                if len(active_stack) < 1:
                    virtual_h1_norm = "virtual_root"
                    active_stack = [virtual_h1_norm]
                    virtual_path = virtual_h1_norm
                    if virtual_path not in seen_paths:
                        chunks.append({
                            "order_index": order_index,
                            "title": "Virtual Root",
                            "content": "Virtual container node.",
                            "parent_path": "",
                            "current_path": virtual_path
                        })
                        seen_paths.add(virtual_path)
                        order_index += 1

                h1_norm = active_stack[0]
                active_stack = [h1_norm, norm_title]
                
                parent_path = h1_norm
                path = f"{parent_path}.{norm_title}"
                seen_paths.add(path)
                
                current_chunk = {
                    "order_index": order_index,
                    "title": title,
                    "content": "",
                    "parent_path": parent_path,
                    "current_path": path
                }
                order_index += 1

            elif h3_match:
                save_current_chunk()
                title = h3_match.group(1).strip()
                norm_title = self._normalize_title(title)
                
                # Check for gaps and inject virtual parent nodes
                if len(active_stack) < 1:
                    # Missing H1 and H2
                    virtual_h1_norm = "virtual_root"
                    virtual_h2_norm = "virtual_sub"
                    active_stack = [virtual_h1_norm, virtual_h2_norm]
                    seen_paths.add(virtual_h1_norm)
                    seen_paths.add(f"{virtual_h1_norm}.{virtual_h2_norm}")
                    chunks.append({
                        "order_index": order_index,
                        "title": "Virtual Root",
                        "content": "Virtual container node.",
                        "parent_path": "",
                        "current_path": virtual_h1_norm
                    })
                    order_index += 1
                    chunks.append({
                        "order_index": order_index,
                        "title": "Virtual Subroot",
                        "content": "Virtual container node.",
                        "parent_path": virtual_h1_norm,
                        "current_path": f"{virtual_h1_norm}.{virtual_h2_norm}"
                    })
                    order_index += 1
                elif len(active_stack) < 2:
                    # Missing H2
                    h1_norm = active_stack[0]
                    virtual_h2_norm = "virtual_sub"
                    active_stack = [h1_norm, virtual_h2_norm]
                    virtual_path = f"{h1_norm}.{virtual_h2_norm}"
                    if virtual_path not in seen_paths:
                        chunks.append({
                            "order_index": order_index,
                            "title": "Virtual Subroot",
                            "content": "Virtual container node.",
                            "parent_path": h1_norm,
                            "current_path": virtual_path
                        })
                        seen_paths.add(virtual_path)
                        order_index += 1

                h1_norm = active_stack[0]
                h2_norm = active_stack[1]
                active_stack = [h1_norm, h2_norm, norm_title]
                
                parent_path = f"{h1_norm}.{h2_norm}"
                path = f"{parent_path}.{norm_title}"
                seen_paths.add(path)
                
                current_chunk = {
                    "order_index": order_index,
                    "title": title,
                    "content": "",
                    "parent_path": parent_path,
                    "current_path": path
                }
                order_index += 1

            else:
                # Text content paragraph or GFM tables
                if not current_chunk:
                    # Ingesting content before H1: create default introductory root chunk
                    norm_title = "overview"
                    active_stack = [norm_title]
                    path = norm_title
                    seen_paths.add(path)
                    current_chunk = {
                        "order_index": order_index,
                        "title": "Overview",
                        "content": "",
                        "parent_path": "",
                        "current_path": path
                    }
                    order_index += 1
                
                if line.strip():
                    current_chunk["content"] += line + "\n"

        save_current_chunk()
        
        # Re-index order indices to guarantee sequential ordering
        for idx, c in enumerate(chunks):
            c["order_index"] = idx
            
        return chunks

    def _classify_operational_mode(self, title: str, content: str) -> str:
        """Classify chunk into operational mode based on content heuristics."""
        text = (title + " " + content).lower()
        
        execution_keywords = {"protocol", "procedure", "checklist", "step", "administer", "dosage", "intake"}
        clarification_keywords = {"pricing", "faq", "explanation", "definition", "overview", "guide"}
        troubleshooting_keywords = {"error", "complication", "adverse", "fallback", "exception", "warning"}
        
        if any(k in text for k in execution_keywords):
            return "EXECUTION"
        elif any(k in text for k in troubleshooting_keywords):
            return "TROUBLESHOOTING"
        elif any(k in text for k in clarification_keywords):
            return "CLARIFICATION"
        return "LEARN"

    def enrich_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage B: Intelligence Enrichment
        Extracts tags, constructs synthetic questions, and computes embeddings.
        """
        content = chunk.get("content", "")
        title = chunk.get("title", "")
        
        # 1. Tags extraction heuristics (words longer than 5 characters matching specific tokens)
        tags = set()
        clean_content = re.sub(r'[^a-zA-Z\s]', '', content)
        words = clean_content.split()
        for w in words:
            w_lower = w.lower()
            if len(w_lower) > 5 and w_lower in ["clinical", "triage", "symptom", "escalation", "priority", "evaluation", "treatment", "protocol", "physician", "patient", "emergency"]:
                tags.add(w_lower)
        
        # Ensure at least a default tag based on section
        if not tags:
            tags.add(chunk["current_path"].split(".")[-1])
        
        # 2. Synthetic question generation heuristics
        synthetic_questions = []
        if content:
            # Generate questions based on section title
            synthetic_questions.append(f"How is {title} evaluated or handled?")
            synthetic_questions.append(f"What protocols are associated with {title}?")
            # Simple content based extraction
            sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 15]
            if sentences:
                synthetic_questions.append(f"What does it mean if: {sentences[0][:80]}...?")
        
        # 3. Compile embedding
        emb = self.embedding_service.get_embedding(f"{title} - {content}")
        
        chunk["chunk_id"] = str(uuid4())
        chunk["tags"] = list(tags)
        chunk["synthetic_questions"] = synthetic_questions
        chunk["embedding"] = emb
        chunk["operational_mode"] = self._classify_operational_mode(title, content)
        return chunk

    async def ingest_raw_text(self, config_id: UUID, raw_text: str) -> List[Dict[str, Any]]:
        # 1. Stage A: Parse skeleton layout
        chunks = self.parse_document(raw_text)
        
        # 2. Stage B: Enrich each chunk
        enriched_chunks = []
        for c in chunks:
            enriched = self.enrich_chunk(c)
            enriched_chunks.append(enriched)
            
        # 3. Persistence: Delete old chunks and insert new ones
        await self.db.delete_knowledge_chunks(config_id)
        await self.db.save_knowledge_chunks(config_id, enriched_chunks)
        
        return enriched_chunks
