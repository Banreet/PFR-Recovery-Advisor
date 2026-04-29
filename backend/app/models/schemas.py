from pydantic import BaseModel
from typing import Optional, List


class OutageRequest(BaseModel):
    description: str
    affected_services: Optional[List[str]] = None
    severity: Optional[str] = "P1"
    additional_context: Optional[str] = None


class RecoveryStep(BaseModel):
    step_number: int
    action: str
    rationale: str
    estimated_duration: str
    risk_level: str  # LOW, MEDIUM, HIGH
    dependencies: List[str]
    verification: str


class RecoveryPlanResponse(BaseModel):
    session_id: str
    summary: str
    affected_services: List[str]
    recovery_steps: List[RecoveryStep]
    warnings: List[str]
    estimated_total_rto: str
    knowledge_sources: List[str]


class ChatMessage(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    updated_steps: Optional[List[RecoveryStep]] = None
