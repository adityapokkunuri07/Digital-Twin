"""
Configuration Routes — Thin HTTP handlers for config management.

Single Responsibility: Parse request → delegate to service → return response.
No business logic lives here.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
import io
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
