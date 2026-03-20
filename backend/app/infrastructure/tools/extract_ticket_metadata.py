from typing import Any, Dict, List, Optional


def extract_ticket_metadata(
    problem_description: str,
    missing_fields: List[str],
    reporter_name: Optional[str] = None,
    device_or_system: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tool 1 — Extract and validate key metadata from a support ticket.

    Evaluates completeness of the ticket by checking essential fields.
    Does NOT invent data — only structures what is explicitly provided.

    Args:
        problem_description: Clear description of the reported problem.
        missing_fields: Fields the LLM identified as absent in the document.
        reporter_name: Full name of the person reporting (None if not found).
        device_or_system: Affected device or system name (None if not found).

    Returns:
        A dict with structured metadata and completeness evaluation.
    """
    CRITICAL_FIELDS = {"problem_description", "device_or_system"}

    has_critical_data = bool(problem_description and problem_description.strip())
    missing_critical = [f for f in missing_fields if f in CRITICAL_FIELDS]

    completeness_score = max(0, 4 - len(missing_fields))  # 0-4 scale
    ticket_is_actionable = has_critical_data and len(missing_critical) == 0

    return {
        "reporter_name": reporter_name or "No especificado",
        "device_or_system": device_or_system or "No especificado",
        "problem_description": problem_description,
        "missing_fields": missing_fields,
        "has_minimum_data": ticket_is_actionable,
        "completeness_score": completeness_score,
        "missing_critical_fields": missing_critical,
    }
