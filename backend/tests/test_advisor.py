from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import RecoveryPlanResponse, RecoveryStep, ChatResponse


client = TestClient(app)


def make_mock_plan(session_id="test-session-123"):
    return RecoveryPlanResponse(
        session_id=session_id,
        summary="Test recovery plan for PilotFish outage",
        affected_services=["PilotFish-Core", "PilotFish-API"],
        recovery_steps=[
            RecoveryStep(
                step_number=1,
                action="Restart Identity-Service",
                rationale="Foundation dependency",
                estimated_duration="2 minutes",
                risk_level="LOW",
                dependencies=[],
                verification="GET /health returns 200",
            )
        ],
        warnings=["Test warning"],
        estimated_total_rto="15 minutes",
        knowledge_sources=["pilotfish_recovery_tsg.json"],
    )


class TestHealthEndpoint:
    def test_health_check_returns_200(self):
        response = client.get("/api/v1/advisor/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAnalyzeEndpoint:
    def test_analyze_returns_recovery_plan(self):
        with patch("app.routers.advisor.ai_service") as mock_ai:
            mock_ai.generate_recovery_plan.return_value = make_mock_plan()
            response = client.post(
                "/api/v1/advisor/analyze",
                json={
                    "description": "PilotFish-Core is down, all health checks failing",
                    "severity": "P1",
                    "affected_services": ["PilotFish-Core"],
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "recovery_steps" in data
        assert len(data["recovery_steps"]) > 0

    def test_analyze_empty_description_returns_400(self):
        response = client.post(
            "/api/v1/advisor/analyze",
            json={"description": "   "},
        )
        assert response.status_code == 400

    def test_analyze_missing_description_returns_422(self):
        response = client.post("/api/v1/advisor/analyze", json={})
        assert response.status_code == 422

    def test_analyze_uses_knowledge_base(self):
        with patch("app.routers.advisor.ai_service") as mock_ai, \
             patch("app.routers.advisor.knowledge_base_service") as mock_kb:
            mock_kb.search_relevant_docs.return_value = ["Relevant doc content"]
            mock_ai.generate_recovery_plan.return_value = make_mock_plan()
            response = client.post(
                "/api/v1/advisor/analyze",
                json={"description": "PilotFish outage P1"},
            )
        assert response.status_code == 200
        mock_kb.search_relevant_docs.assert_called_once()


class TestChatEndpoint:
    def test_chat_invalid_session_returns_404(self):
        response = client.post(
            "/api/v1/advisor/chat",
            json={"session_id": "nonexistent-session", "message": "What should I do next?"},
        )
        assert response.status_code == 404

    def test_chat_valid_session_returns_response(self):
        with patch("app.routers.advisor.ai_service") as mock_ai:
            mock_plan = make_mock_plan("chat-test-session")
            mock_ai.generate_recovery_plan.return_value = mock_plan
            analyze_resp = client.post(
                "/api/v1/advisor/analyze",
                json={"description": "PilotFish outage for chat test"},
            )
            assert analyze_resp.status_code == 200
            session_id = analyze_resp.json()["session_id"]

            mock_ai.chat_followup.return_value = ChatResponse(
                session_id=session_id,
                response="Here is the next step to take...",
            )
            chat_resp = client.post(
                "/api/v1/advisor/chat",
                json={"session_id": session_id, "message": "What is the risk of step 3?"},
            )
        assert chat_resp.status_code == 200
        assert "response" in chat_resp.json()

    def test_chat_empty_message_returns_400(self):
        with patch("app.routers.advisor.ai_service") as mock_ai:
            mock_plan = make_mock_plan("empty-msg-session")
            mock_ai.generate_recovery_plan.return_value = mock_plan
            analyze_resp = client.post(
                "/api/v1/advisor/analyze",
                json={"description": "PilotFish outage for empty message test"},
            )
            session_id = analyze_resp.json()["session_id"]

        response = client.post(
            "/api/v1/advisor/chat",
            json={"session_id": session_id, "message": ""},
        )
        assert response.status_code == 400


class TestKnowledgeBase:
    def test_knowledge_base_loads_documents(self):
        from app.services.knowledge_base import KnowledgeBaseService
        kb = KnowledgeBaseService()
        assert len(kb.documents) > 0

    def test_search_returns_relevant_results(self):
        from app.services.knowledge_base import KnowledgeBaseService
        kb = KnowledgeBaseService()
        results = kb.search_relevant_docs("PilotFish recovery restart")
        assert isinstance(results, list)

    def test_get_service_dependencies(self):
        from app.services.knowledge_base import KnowledgeBaseService
        kb = KnowledgeBaseService()
        deps = kb.get_service_dependencies()
        assert isinstance(deps, dict)
        assert "PilotFish-Core" in deps
