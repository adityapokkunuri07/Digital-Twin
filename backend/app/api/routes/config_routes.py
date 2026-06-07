"""
Configuration Routes — Thin HTTP handlers for config management.

Single Responsibility: Parse request → delegate to service → return response.
No business logic lives here.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
import io
import os
import fitz  # PyMuPDF
import re

# Suppress non-fatal C-level warnings (like zlib incorrect header) from flooding the terminal
fitz.TOOLS.mupdf_display_errors(False)

from uuid import UUID
from google import genai
from google.genai import types
from backend.app.core.config import settings

from backend.app.api.schemas.config_schemas import (
    ValidateConfigRequest,
    SaveConfigRequest,
    IngestDocumentRequest,
    UnlearnRequest,
)
from backend.app.api.dependencies import (
    get_config_service,
    get_unlearning_service,
    get_ingestion_pipeline,
    get_config_repo,
    get_cot_repo,
    get_knowledge_repo,
    get_export_service,
)
from backend.app.services.config_service import ConfigService
from backend.app.services.unlearning_service import UnlearningService
from backend.app.services.ingestion_service import StructuralRAGIngestionPipeline

router = APIRouter(prefix="/config", tags=["Configuration"])


def apply_ai_structure(raw_text: str, client: genai.Client) -> str:
    """Uses Gemini to structure flat text into hierarchical Markdown."""
    if re.search(r'^#{1,3}\s+', raw_text, re.MULTILINE):
        return raw_text
        
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                "You are an expert Document Structurer. Format the following text into hierarchical Markdown using #, ##, ### headers based on logical sections, chapters, or topics. Do not alter the underlying text. Output ONLY the markdown text.",
                raw_text
            ]
        )
        structured = response.text.strip()
        if structured.startswith("```markdown"):
            structured = structured[11:-3].strip()
        elif structured.startswith("```"):
            structured = structured[3:-3].strip()
        return structured
    except Exception as e:
        print(f"AI Structuring failed: {e}")
        return raw_text


@router.post("/validate")
def validate_config(
    payload: ValidateConfigRequest,
    config_svc: ConfigService = Depends(get_config_service),
):
    """Validate a workflow configuration for feasibility (cycle detection, input coverage)."""
    is_feasible, errors = config_svc.validate_config(payload.workflow_config)
    return {"is_feasible": is_feasible, "errors": errors}


@router.post("/save")
async def save_config(
    payload: SaveConfigRequest,
    config_svc: ConfigService = Depends(get_config_service),
):
    """Validate, persist, and project a twin configuration to the audit plane."""
    result = await config_svc.save_config(
        payload.config_id, payload.doctor_id,
        payload.workflow_config, payload.active_version,
    )
    return result


@router.post("/ingest")
async def ingest_document(
    payload: IngestDocumentRequest,
    pipeline: StructuralRAGIngestionPipeline = Depends(get_ingestion_pipeline),
):
    """Ingest raw text through the structural RAG pipeline (Stage A + B)."""
    chunks = await pipeline.ingest_raw_text(payload.config_id, payload.raw_text)

    # Strip embedding floats from API return payload to reduce bandwidth
    clean_chunks = []
    for c in chunks:
        cc = c.copy()
        cc.pop("embedding", None)
        clean_chunks.append(cc)

    return {
        "status": "success",
        "chunks_ingested": len(clean_chunks),
        "chunks": clean_chunks,
    }


@router.post("/upload")
async def upload_document(
    config_id: UUID = Form(...),
    file: UploadFile = File(...),
    pipeline: StructuralRAGIngestionPipeline = Depends(get_ingestion_pipeline),
):
    """Ingest a file (PDF, TXT, MD) by extracting text and passing it to the pipeline."""
    contents = await file.read()
    raw_text = ""

    if file.filename.lower().endswith(".pdf"):
        try:
            doc = fitz.open("pdf", contents)
            client = None
            for page in doc:
                text = page.get_text().strip()
                if not text:
                    # Fallback to OCR using Gemini Vision
                    try:
                        if not client:
                            client = genai.Client(api_key=settings.GEMINI_API_KEY)
                        pix = page.get_pixmap()
                        img_bytes = pix.tobytes("png")
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=[
                                types.Part.from_bytes(data=img_bytes, mime_type='image/png'),
                                "Extract all the text from this clinical document page exactly as written. Preserve formatting."
                            ]
                        )
                        text = response.text
                    except Exception as e:
                        print(f"Gemini OCR Failed on page: {e}")
                if text:
                    raw_text += text + "\n"
            doc.close()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
    else:
        try:
            raw_text = contents.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be a valid UTF-8 text file or PDF.")
            
    if not raw_text.strip():
        if file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="No readable text found. If this is a scanned PDF, it requires OCR which is not yet supported.")
        raise HTTPException(status_code=400, detail="No readable text found in the uploaded file.")

    # Apply AI Structuring
    genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    structured_text = apply_ai_structure(raw_text, genai_client)

    chunks = await pipeline.ingest_raw_text(config_id, structured_text)

    clean_chunks = []
    for c in chunks:
        cc = c.copy()
        cc.pop("embedding", None)
        clean_chunks.append(cc)

    return {
        "status": "success",
        "chunks_ingested": len(clean_chunks),
        "chunks": clean_chunks,
        "raw_text": structured_text
    }


@router.post("/{config_id}/unlearn")
async def unlearn_nodes(
    config_id: UUID,
    payload: UnlearnRequest,
    unlearning_svc: UnlearningService = Depends(get_unlearning_service),
):
    """
    Execute the Mom & Child Unlearning Protocol (Vector Tombstoning).
    Sets vector embedding = NULL for specified node IDs while retaining structure,
    attaches unlearning rationale, and projects changes to Obsidian.
    """
    result = await unlearning_svc.unlearn_nodes(
        config_id, payload.node_ids, payload.rationale,
    )
    return result


@router.get("/sync")
async def sync_obsidian(
    config_repo = Depends(get_config_repo),
    cot_repo = Depends(get_cot_repo),
    knowledge_repo = Depends(get_knowledge_repo),
    export_svc = Depends(get_export_service),
):
    """
    Synchronizes the database state to the local Obsidian vault files on disk
    and returns a complete list of all mapped files in the format expected by the frontend.
    """
    use_mock = config_repo.use_mock

    # 1. Fetch configs, CoT nodes/edges, and knowledge chunks
    if use_mock:
        configs_list = list(config_repo._configs.values())

        # Flatten all values from dict-of-lists
        all_nodes = []
        for n_list in cot_repo._cot_nodes.values():
            all_nodes.extend(n_list)

        all_edges = []
        for e_list in cot_repo._cot_edges.values():
            all_edges.extend(e_list)

        all_chunks = []
        for c_list in knowledge_repo._knowledge_chunks.values():
            all_chunks.extend(c_list)
    else:
        client = config_repo.client
        configs_list = client.table("expert_twin_configs").select("*").execute().data or []
        all_nodes = client.table("cot_nodes").select("*").execute().data or []
        all_edges = client.table("cot_edges").select("*").execute().data or []
        all_chunks = client.table("knowledge_chunks").select("*").execute().data or []

    # 2. Write to local Obsidian vault on disk
    vault_path = export_svc.vault_path
    os.makedirs(os.path.join(vault_path, "configs"), exist_ok=True)
    os.makedirs(os.path.join(vault_path, "cot_nodes"), exist_ok=True)
    os.makedirs(os.path.join(vault_path, "knowledge"), exist_ok=True)

    # For each config, export it along with its nodes and edges
    for config in configs_list:
        config_id_str = str(config.get("config_id"))
        config_nodes = [n for n in all_nodes if str(n.get("config_id")) == config_id_str]
        config_edges = [e for e in all_edges if str(e.get("config_id")) == config_id_str]
        try:
            export_svc.export_config(config, config_nodes, config_edges)
        except Exception as e:
            pass

    # For each knowledge chunk, write to disk under knowledge/
    for chunk in all_chunks:
        chunk_id = str(chunk.get("chunk_id"))
        parent_path = chunk.get("parent_path", "")
        title = chunk.get("title", "")
        content = chunk.get("content", "")
        tags = chunk.get("tags", [])
        synthetic_questions = chunk.get("synthetic_questions", [])
        first_q = synthetic_questions[0] if synthetic_questions else ""

        filename_part = parent_path if parent_path else title.lower().replace(" ", "_")
        # Ensure filename is safe
        filename_part = "".join([c for c in filename_part if c.isalnum() or c in ".-_"])
        chunk_filepath = os.path.join(vault_path, "knowledge", f"{filename_part}.md")

        # Build YAML frontmatter markdown
        yaml_frontmatter = (
            "---\n"
            f'node_id: "{chunk_id}"\n'
            f'parent_id: "{parent_path or "root"}"\n'
            'sync_status: "verified"\n'
            "chain_of_thought: |\n"
            f'  "{first_q}"\n'
            f'tags: [{", ".join(tags)}]\n'
            "quarantine_status: false\n"
            "---\n\n"
            f"# {title}\n"
            f"{content}\n"
        )

        try:
            with open(chunk_filepath, "w", encoding="utf-8") as f:
                f.write(yaml_frontmatter)
        except Exception as e:
            pass

    # 3. Compile the response list of files for the frontend
    files_response = []

    # Format configs
    for config in configs_list:
        config_id = str(config.get("config_id"))
        active_version = config.get("active_version", "1.0.0")
        workflow_config = config.get("workflow_config", {}) or {}
        steps = workflow_config.get("steps", [])
        files_response.append({
            "path": f"configs/config_{config_id}.md",
            "type": "config",
            "node_id": config_id,
            "title": f"Workflow Config {active_version}",
            "content": f"Configuration for Dr. Sterling.\nNodes: {len(steps)}",
            "tags": ["config", "workflow"]
        })

    # Format CoT nodes
    for node in all_nodes:
        node_id = str(node.get("node_id"))
        meta = node.get("metadata", {}) or {}
        files_response.append({
            "path": f"cot_nodes/node_{node_id}.md",
            "type": "cot",
            "node_id": node_id,
            "parent_id": "",
            "title": node.get("title", ""),
            "content": node.get("content", ""),
            "tags": ["onboarding"],
            "chain_of_thought": "",
            "quarantine_status": meta.get("unlearned", False),
            "unlearning_rationale": meta.get("unlearning_reason", "")
        })

    # Format Knowledge chunks
    for chunk in all_chunks:
        chunk_id = str(chunk.get("chunk_id"))
        parent_path = chunk.get("parent_path", "")
        title = chunk.get("title", "")
        tags = chunk.get("tags", [])
        synthetic_questions = chunk.get("synthetic_questions", [])
        first_q = synthetic_questions[0] if synthetic_questions else ""

        filename_part = parent_path if parent_path else title.lower().replace(" ", "_")
        filename_part = "".join([c for c in filename_part if c.isalnum() or c in ".-_"])

        files_response.append({
            "path": f"knowledge/{filename_part}.md",
            "type": "knowledge",
            "node_id": chunk_id,
            "parent_id": parent_path,
            "title": title,
            "content": chunk.get("content", ""),
            "tags": tags,
            "chain_of_thought": first_q,
            "quarantine_status": False,
            "unlearning_rationale": ""
        })

    return {"status": "success", "files": files_response}
