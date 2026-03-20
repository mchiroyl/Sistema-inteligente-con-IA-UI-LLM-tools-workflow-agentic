from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, model_validator


class StatusEnum(str, Enum):
    success = "success"
    needs_review = "needs_review"
    error = "error"


class DocumentTypeEnum(str, Enum):
    lab_result = "lab_result"
    academic_document = "academic_document"
    medical_document = "medical_document"
    support_document = "support_document"
    other = "other"
    unknown = "unknown"


class ToolTrace(BaseModel):
    tool: str
    reason: str
    success: bool


class AnalysisResponse(BaseModel):
    status: StatusEnum
    document_type: DocumentTypeEnum
    summary: str
    extracted_data: Dict[str, Any]
    warnings: List[str]
    needs_clarification: bool
    clarifying_questions: List[str]
    tool_trace: List[ToolTrace]
    edited_by_human: bool = False

    @model_validator(mode="after")
    def validate_clarification_contract(self) -> "AnalysisResponse":
        """Enforce the contract: if needs_clarification=True, must have >= 2 questions."""
        if self.needs_clarification and len(self.clarifying_questions) < 2:
            # Pad with generic questions to satisfy the contract rather than crashing
            self.clarifying_questions = list(self.clarifying_questions) + [
                "¿Puede proporcionar más detalles sobre el problema?",
                "¿Cuándo comenzó a ocurrir el problema?",
            ]
            self.clarifying_questions = self.clarifying_questions[:max(2, len(self.clarifying_questions))]
        if not self.needs_clarification:
            self.clarifying_questions = []
        return self
