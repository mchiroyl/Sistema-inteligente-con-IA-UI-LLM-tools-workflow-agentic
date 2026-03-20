import json
import logging
from datetime import datetime
from pathlib import Path

from app.domain.models import AnalysisResponse

logger = logging.getLogger(__name__)

# Almacenamiento persistente
HISTORY_FILE = Path(__file__).parent.parent.parent / "historial_tickets.json"

def save_to_history(filename: str, result: AnalysisResponse):
    """Guarda un resultado de análisis en el archivo de historial."""
    try:
        # Cargar historial existente
        history = []
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    history = json.loads(content)
        
        # Crear nueva entrada
        entry = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "status": result.status.value,
            "document_type": result.document_type.value,
            "summary": result.summary,
            "extracted_data": result.extracted_data,
            "warnings": result.warnings,
            "needs_clarification": result.needs_clarification,
            "clarifying_questions": result.clarifying_questions,
            "tool_trace": [trace.model_dump() for trace in result.tool_trace]
        }
        
        # Agregar al inicio de la lista
        history.insert(0, entry)
        
        # Guardar archivo
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"Error saving to history: {str(e)}", exc_info=True)

def get_history() -> list:
    """Obtiene el historial completo de tickets analizados."""
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        return []
    except Exception as e:
        logger.error(f"Error reading history: {str(e)}", exc_info=True)
        return []

def update_history_item(index: int, updated_data: dict) -> bool:
    """Actualiza una entrada específica del historial por su índice."""
    try:
        history = get_history()
        if 0 <= index < len(history):
            # Preservar campos que no deben cambiar sin control
            history[index].update(updated_data)
            history[index]["edited_by_human"] = True
            
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating history item: {str(e)}", exc_info=True)
        return False
