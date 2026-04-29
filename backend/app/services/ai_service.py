import os
import json
import uuid
from typing import Optional
from dotenv import load_dotenv

from app.models.schemas import (
    OutageRequest,
    RecoveryStep,
    RecoveryPlanResponse,
    ChatResponse,
)

load_dotenv()


def _get_mock_recovery_plan(outage: OutageRequest) -> RecoveryPlanResponse:
    affected = outage.affected_services or ["PilotFish-Core", "PilotFish-API"]
    return RecoveryPlanResponse(
        session_id=str(uuid.uuid4()),
        summary=(
            f"[DEMO MODE] Recovery plan for: {outage.description[:100]}. "
            "Configure AZURE_OPENAI_API_KEY or OPENAI_API_KEY for AI-powered plans."
        ),
        affected_services=affected,
        recovery_steps=[
            RecoveryStep(
                step_number=1,
                action="Verify Identity-Service and Config-Service health",
                rationale="These are foundational dependencies required before PilotFish-Core can start.",
                estimated_duration="5 minutes",
                risk_level="LOW",
                dependencies=[],
                verification="GET /health returns 200 on both services.",
            ),
            RecoveryStep(
                step_number=2,
                action="Restart Storage-Service and confirm data integrity",
                rationale="Storage-Service must be healthy before core services attempt connections.",
                estimated_duration="10 minutes",
                risk_level="MEDIUM",
                dependencies=["Identity-Service"],
                verification="Check storage health endpoint and run integrity check script.",
            ),
            RecoveryStep(
                step_number=3,
                action="Restart PilotFish-Core",
                rationale="Core service can now start with all dependencies healthy.",
                estimated_duration="3 minutes",
                risk_level="HIGH",
                dependencies=["Identity-Service", "Config-Service", "Storage-Service"],
                verification="GET /health returns 200 and logs show 'Ready'.",
            ),
            RecoveryStep(
                step_number=4,
                action="Restart PilotFish-API",
                rationale="API layer depends on Core being fully operational.",
                estimated_duration="2 minutes",
                risk_level="MEDIUM",
                dependencies=["PilotFish-Core"],
                verification="Run smoke tests against /api/v1/status endpoint.",
            ),
            RecoveryStep(
                step_number=5,
                action="Restart PilotFish-Scheduler and PilotFish-Agent",
                rationale="Secondary services restored after primary plane is stable.",
                estimated_duration="5 minutes",
                risk_level="LOW",
                dependencies=["PilotFish-Core", "PilotFish-API"],
                verification="Confirm scheduled jobs resume and agents check in.",
            ),
        ],
        warnings=[
            "DEMO MODE: No AI API key configured. Plan is illustrative.",
            "Always confirm runbook steps with team lead before executing in production.",
        ],
        estimated_total_rto="25 minutes",
        knowledge_sources=["pilotfish_recovery_tsg.json", "service_dependencies.json"],
    )


class AIService:
    def __init__(self):
        self.client = None
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        self._init_client()

    def _init_client(self):
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        try:
            if azure_endpoint and azure_key:
                from openai import AzureOpenAI
                self.client = AzureOpenAI(
                    azure_endpoint=azure_endpoint,
                    api_key=azure_key,
                    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                )
                self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
            elif openai_key:
                from openai import OpenAI
                self.client = OpenAI(api_key=openai_key)
                self.deployment = "gpt-4o"
        except Exception:
            self.client = None

    def generate_recovery_plan(
        self, outage: OutageRequest, kb_context: str
    ) -> RecoveryPlanResponse:
        if self.client is None:
            return _get_mock_recovery_plan(outage)

        session_id = str(uuid.uuid4())
        system_prompt = (
            "You are an expert PilotFish DRI (Designated Responsible Individual) "
            "with deep knowledge of control plane recovery. Generate structured, "
            "dependency-aware recovery plans. Always respond with valid JSON matching "
            "the requested schema exactly."
        )
        user_prompt = f"""Outage Description: {outage.description}
Severity: {outage.severity}
Affected Services: {', '.join(outage.affected_services or ['Unknown'])}
Additional Context: {outage.additional_context or 'None'}

Knowledge Base Context:
{kb_context}

Generate a recovery plan as JSON with this exact structure:
{{
  "summary": "...",
  "affected_services": ["..."],
  "recovery_steps": [
    {{
      "step_number": 1,
      "action": "...",
      "rationale": "...",
      "estimated_duration": "...",
      "risk_level": "LOW|MEDIUM|HIGH",
      "dependencies": ["..."],
      "verification": "..."
    }}
  ],
  "warnings": ["..."],
  "estimated_total_rto": "...",
  "knowledge_sources": ["..."]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            data = json.loads(response.choices[0].message.content)
            steps = [RecoveryStep(**s) for s in data.get("recovery_steps", [])]
            return RecoveryPlanResponse(
                session_id=session_id,
                summary=data.get("summary", ""),
                affected_services=data.get("affected_services", []),
                recovery_steps=steps,
                warnings=data.get("warnings", []),
                estimated_total_rto=data.get("estimated_total_rto", "Unknown"),
                knowledge_sources=data.get("knowledge_sources", []),
            )
        except Exception as e:
            plan = _get_mock_recovery_plan(outage)
            plan.session_id = session_id
            plan.warnings.append(f"AI generation failed: {str(e)[:100]}")
            return plan

    def chat_followup(
        self, session_id: str, message: str, history: list
    ) -> ChatResponse:
        if self.client is None:
            return ChatResponse(
                session_id=session_id,
                response=(
                    "[DEMO MODE] Chat requires a configured AI API key. "
                    "Set AZURE_OPENAI_API_KEY or OPENAI_API_KEY in your .env file. "
                    f"Your question was: '{message}'"
                ),
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert PilotFish DRI assistant helping with control plane "
                    "recovery. Answer follow-up questions concisely and accurately."
                ),
            }
        ] + history + [{"role": "user", "content": message}]

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=0.3,
            )
            return ChatResponse(
                session_id=session_id,
                response=response.choices[0].message.content,
            )
        except Exception as e:
            return ChatResponse(
                session_id=session_id,
                response=f"Error generating response: {str(e)[:200]}",
            )


ai_service = AIService()
