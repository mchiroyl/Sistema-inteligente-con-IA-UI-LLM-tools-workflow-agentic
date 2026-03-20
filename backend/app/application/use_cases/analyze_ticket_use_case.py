"""
Agentic Orchestrator — Support Intake AI
=========================================
Manages the full agentic loop:
  1. Build context from the extracted file content
  2. Call the LLM with tool definitions (OpenAI function calling)
  3. Execute tools upon request (extract_ticket_metadata, check_support_policy)
  4. Repeat until the LLM produces a final structured JSON answer
  5. Parse, validate via Pydantic, and return AnalysisResponse
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.domain.models import (
    AnalysisResponse,
    DocumentTypeEnum,
    StatusEnum,
    ToolTrace,
)
from app.infrastructure.tools.check_support_policy import check_support_policy
from app.infrastructure.tools.extract_ticket_metadata import extract_ticket_metadata

load_dotenv()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  OpenAI / OpenRouter client
# ─────────────────────────────────────────────────────────────────────────────
_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", ""),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
)
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ─────────────────────────────────────────────────────────────────────────────
#  Tool definitions (OpenAI function-calling schema)
# ─────────────────────────────────────────────────────────────────────────────
TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "extract_ticket_metadata",
            "description": (
                "Extrae y valida los metadatos clave de un ticket de soporte técnico: "
                "nombre del reportante, dispositivo o sistema afectado, descripción del "
                "problema y lista de campos faltantes. SIEMPRE debe ser la primera herramienta invocada."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reporter_name": {
                        "type": "string",
                        "description": "Nombre de quien reporta. null si no se menciona.",
                    },
                    "device_or_system": {
                        "type": "string",
                        "description": "Dispositivo o sistema afectado (ej: 'Laptop HP ProBook', 'ERP SAP'). null si no se especifica.",
                    },
                    "problem_description": {
                        "type": "string",
                        "description": "Descripción clara y literal del problema reportado. Extraer del documento, sin inventar.",
                    },
                    "missing_fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Campos importantes ausentes: 'reporter_name', 'device_or_system', 'location', 'error_code', etc.",
                    },
                },
                "required": ["problem_description", "missing_fields"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_support_policy",
            "description": (
                "Consulta la base de datos de políticas de soporte institucional. "
                "Determina la prioridad del ticket (Crítica/Alta/Media/Baja) y la acción "
                "sugerida según el tipo de problema. Invocar DESPUÉS de extract_ticket_metadata."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "problem_description": {
                        "type": "string",
                        "description": "Descripción del problema para determinar la prioridad.",
                    },
                    "device_or_system": {
                        "type": "string",
                        "description": "Dispositivo o sistema afectado (mejora la detección de política).",
                    },
                },
                "required": ["problem_description"],
            },
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
#  System prompt
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un agente experto en recepción y análisis de tickets de soporte técnico institucional.

REGLAS CRÍTICAS — CIBERSEGURIDAD Y ÉTICA:
1. NUNCA inventes, asumas ni completes datos que no estén explícitamente en el documento.
2. Si un campo no está en el texto, márcalo como ausente o "No especificado".
3. No proceses ni guardes información sensible fuera de lo necesario para el análisis.

FLUJO OBLIGATORIO:
1. Llama a `extract_ticket_metadata` SIEMPRE primero.
2. Luego llama a `check_support_policy` con la descripción obtenida.
3. Tras usar ambas herramientas, produce un JSON final.

CRITERIOS DE STATUS - REGLA DE ORO:
- "success": Descripcion clara del problema Y datos suficientes para abrirlo (minimo: descripcion especifica + dispositivo o sistema).
- "needs_review": El documento INTENTA reportar un problema de soporte (menciona: problema, error, ayuda, sistema, no funciona, acceder, no puedo, TI, soporte, falla) PERO le faltan datos criticos. USA ESTE STATUS cuando haya cualquier intencion de soporte aunque sea vaga.
- "error": SOLO para contenido definitivamente fuera de contexto (no es soporte en absoluto) o completamente ilegible/vacio.

REGLA CRITICA: Si el texto contiene palabras relacionadas con soporte tecnico, usa needs_review (nunca error) cuando falten datos.

FORMATO DE RESPUESTA FINAL (JSON puro, sin markdown):
{
  "status": "success|needs_review|error",
  "document_type": "support_document",
  "summary": "Resumen breve y claro en español",
  "extracted_data": {
    "reporter_name": "...",
    "device_or_system": "...",
    "problem_description": "...",
    "priority": "...",
    "suggested_action": "..."
  },
  "warnings": ["lista de advertencias, puede estar vacía"],
  "needs_clarification": true/false,
  "clarifying_questions": ["pregunta 1", "pregunta 2"]
}

REGLA: Si needs_clarification=true MINIMO 2 preguntas muy especificas (que dato falta exactamente).
REGLA: Si needs_clarification=false entonces clarifying_questions = []
REGLA: status needs_review SIEMPRE implica needs_clarification=true.
REGLA: Responde SOLO con el JSON final. Sin explicaciones ni bloques de codigo markdown."""


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _build_user_message(extracted_text: str, filename: str) -> Any:
    """Build the correct user message for text or image content."""
    if extracted_text.startswith("__IMAGE_BASE64__:"):
        parts = extracted_text.split(":", 2)
        if len(parts) == 3:
            _, mime, b64 = parts
            return [
                {
                    "type": "text",
                    "text": (
                        f"Analiza este documento de soporte técnico (archivo: {filename}). "
                        "Extrae ÚNICAMENTE la información que esté claramente visible. "
                        "No inventes ni supongas datos ausentes."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime};base64,{b64}",
                        "detail": "low",
                    },
                },
            ]
    # Plain text content
    return (
        f"Analiza este ticket/documento de soporte técnico (archivo: {filename}):\n\n"
        f"{extracted_text}"
    )


def _call_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool and return its result dict."""
    if tool_name == "extract_ticket_metadata":
        return extract_ticket_metadata(**tool_args)
    elif tool_name == "check_support_policy":
        return check_support_policy(**tool_args)
    else:
        return {"error": f"Herramienta '{tool_name}' no reconocida."}


# ─────────────────────────────────────────────────────────────────────────────
#  Main agentic workflow
# ─────────────────────────────────────────────────────────────────────────────
async def run_agentic_workflow(
    extracted_text: str,
    extraction_warning: Optional[str],
    filename: str,
) -> AnalysisResponse:
    """
    Orchestrates the full agentic loop:
      - LLM calls tools as needed
      - Tools are executed locally
      - Results feed back to LLM
      - Final structured JSON is validated by Pydantic
    """
    tool_trace: List[ToolTrace] = []
    warnings: List[str] = []

    if extraction_warning:
        warnings.append(extraction_warning)

    # Guard: empty content after processing
    is_image = extracted_text.startswith("__IMAGE_BASE64__:")
    if not extracted_text.strip() and not is_image:
        return AnalysisResponse(
            status=StatusEnum.error,
            document_type=DocumentTypeEnum.unknown,
            summary="No se pudo extraer contenido del documento.",
            extracted_data={},
            warnings=["El documento no contiene texto legible o está dañado."],
            needs_clarification=False,
            clarifying_questions=[],
            tool_trace=[],
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_message(extracted_text, filename)},
    ]

    final_text = ""
    max_iterations = 6

    # ── Agentic loop ──────────────────────────────────────────────────────────
    for iteration in range(max_iterations):
        response = await _client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.1,
            max_tokens=2000,
        )

        assistant_msg = response.choices[0].message

        # Serialize assistant message for the conversation history
        msg_dict: Dict[str, Any] = {"role": "assistant"}
        if assistant_msg.content:
            msg_dict["content"] = assistant_msg.content
        if assistant_msg.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant_msg.tool_calls
            ]
        messages.append(msg_dict)

        # No tool calls → LLM produced the final answer
        if not assistant_msg.tool_calls:
            final_text = assistant_msg.content or "{}"
            break

        # Execute each tool the LLM requested
        for tool_call in assistant_msg.tool_calls:
            t_name = tool_call.function.name
            try:
                t_args = json.loads(tool_call.function.arguments)
                result = _call_tool(t_name, t_args)
                success = "error" not in result
                reason = _trace_reason(t_name, result)
            except Exception as exc:
                result = {"error": str(exc)}
                success = False
                reason = f"Error al ejecutar: {exc}"

            tool_trace.append(ToolTrace(tool=t_name, reason=reason, success=success))

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    # ── Parse final JSON response ─────────────────────────────────────────────
    try:
        json_match = re.search(r"\{.*\}", final_text, re.DOTALL)
        if not json_match:
            raise ValueError("No se encontró JSON en la respuesta del LLM.")
        parsed = json.loads(json_match.group())

        # Enforce contract fields
        parsed["document_type"] = "support_document"
        parsed["tool_trace"] = [t.model_dump() for t in tool_trace]

        # Merge extraction warnings
        parsed.setdefault("warnings", [])
        parsed["warnings"] = warnings + parsed["warnings"]

        return AnalysisResponse(**parsed)

    except Exception as exc:
        logger.error("Error parsing LLM output: %s | raw: %s", exc, final_text[:300])
        warnings.append(f"Error interno al estructurar la respuesta: {exc}")
        return AnalysisResponse(
            status=StatusEnum.error,
            document_type=DocumentTypeEnum.support_document,
            summary="Error interno al procesar la respuesta del modelo.",
            extracted_data={},
            warnings=warnings,
            needs_clarification=False,
            clarifying_questions=[],
            tool_trace=tool_trace,
        )


def _trace_reason(tool_name: str, result: Dict[str, Any]) -> str:
    """Generate a human-readable trace reason from tool results."""
    if tool_name == "extract_ticket_metadata":
        score = result.get("completeness_score", "?")
        missing = result.get("missing_fields", [])
        return f"Extracción completada. Completitud: {score}/4. Faltantes: {missing or 'ninguno'}."
    elif tool_name == "check_support_policy":
        priority = result.get("priority", "?")
        matched = result.get("matched_keyword", "general")
        return f"Política evaluada: prioridad '{priority}' (coincidencia: '{matched}')."
    return "Herramienta ejecutada."
