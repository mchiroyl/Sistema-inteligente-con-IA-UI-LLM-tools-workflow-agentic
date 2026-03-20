import logging
import os
from fastapi import APIRouter, File, UploadFile

from app.domain.models import AnalysisResponse, DocumentTypeEnum, StatusEnum
from app.application.file_processor import extract_content_from_file
from app.application.use_cases.analyze_ticket_use_case import run_agentic_workflow
from app.infrastructure.persistence.ticket_repository import save_to_history, get_history, update_history_item

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tickets"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _error_response(user_message: str, warning: str, filename: str = "documento") -> AnalysisResponse:
    res = AnalysisResponse(
        status=StatusEnum.error,
        document_type=DocumentTypeEnum.unknown,
        summary=user_message,
        extracted_data={},
        warnings=[warning],
        needs_clarification=False,
        clarifying_questions=[],
        tool_trace=[],
    )
    save_to_history(filename, res)
    return res


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_document(file: UploadFile = File(...)):
    """Analyze a support ticket document (PDF, image, or text)."""
    _, ext = os.path.splitext((file.filename or "").lower())
    if ext not in ALLOWED_EXTENSIONS:
        return _error_response(
            "Tipo de archivo no permitido.",
            f"La extensión '{ext}' no está autorizada. Use: PDF, PNG, JPG, JPEG, TXT.",
            file.filename or "documento"
        )

    try:
        content = await file.read()
    except Exception:
        return _error_response(
            "Error al leer el archivo.",
            "No se pudo leer el contenido del archivo enviado.",
            file.filename or "documento"
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        return _error_response(
            "Archivo demasiado grande.",
            f"El archivo supera el límite de 5 MB ({len(content) // 1024} KB recibidos).",
            file.filename or "documento"
        )

    if len(content) == 0:
        return _error_response(
            "El archivo está vacío.",
            "El archivo recibido no contiene datos. Verifique que el archivo sea válido.",
            file.filename or "documento"
        )

    logger.info("Processing file: %s | size: %d bytes | ext: %s", file.filename, len(content), ext)

    try:
        extracted_text, extraction_warning = extract_content_from_file(
            content, ext, file.filename or "documento"
        )
        result = await run_agentic_workflow(
            extracted_text, extraction_warning, file.filename or "documento"
        )
        save_to_history(file.filename or "documento", result)
        logger.info("Analysis complete: status=%s", result.status)
        return result

    except Exception as exc:
        logger.error("Unhandled error processing %s: %s", file.filename, str(exc), exc_info=True)
        return _error_response(
            "Error interno al procesar el documento.",
            "Ocurrió un error inesperado. Por favor intente de nuevo.",
            file.filename or "documento"
        )


@router.get("/history")
async def api_get_history():
    """Retrieve the history of all processed documents."""
    return get_history()


@router.put("/history/{index}")
async def api_update_history(index: int, updated_data: dict):
    """Update a specific history item by its index."""
    success = update_history_item(index, updated_data)
    if success:
        return {"status": "success", "message": "Ticket actualizado correctamente."}
    return {"status": "error", "message": "No se pudo actualizar el ticket."}
