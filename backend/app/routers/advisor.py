from fastapi import APIRouter, HTTPException
from typing import Dict, List
from app.models.schemas import (
    OutageRequest,
    RecoveryPlanResponse,
    ChatMessage,
    ChatResponse,
)
from app.services.ai_service import ai_service
from app.services.knowledge_base import knowledge_base_service

router = APIRouter(prefix="/advisor", tags=["advisor"])

# In-memory session store: session_id -> {plan, history}
sessions: Dict[str, dict] = {}


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "PFR Recovery Advisor"}


@router.post("/analyze", response_model=RecoveryPlanResponse)
async def analyze_outage(request: OutageRequest):
    if not request.description or not request.description.strip():
        raise HTTPException(status_code=400, detail="Outage description is required.")

    kb_docs = knowledge_base_service.search_relevant_docs(request.description)
    kb_context = "\n\n".join(kb_docs) if kb_docs else "No relevant documents found."

    plan = ai_service.generate_recovery_plan(request, kb_context)

    sessions[plan.session_id] = {
        "plan": plan,
        "history": [
            {
                "role": "assistant",
                "content": f"Recovery plan generated. Summary: {plan.summary}",
            }
        ],
        "outage": request,
    }

    return plan


@router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    if not message.session_id or message.session_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please analyze an outage first.",
        )
    if not message.message or not message.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session = sessions[message.session_id]
    history = session.get("history", [])

    response = ai_service.chat_followup(
        session_id=message.session_id,
        message=message.message,
        history=history,
    )

    history.append({"role": "user", "content": message.message})
    history.append({"role": "assistant", "content": response.response})
    session["history"] = history

    return response
