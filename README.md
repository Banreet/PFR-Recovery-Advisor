# PFR Recovery Advisor

> AI-powered recovery advisor for PilotFish control plane outages — helping on-call DRIs recover faster with dependency-aware, step-by-step recovery plans.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                     Browser                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ OutageForm  │  │ RecoveryPlan │  │    Chat    │ │
│  └──────┬──────┘  └──────┬───────┘  └─────┬──────┘ │
└─────────┼────────────────┼────────────────┼────────┘
          │ HTTP/REST       │                │
┌─────────▼────────────────▼────────────────▼────────┐
│              FastAPI Backend (:8000)                 │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │  AI Service  │  │  KnowledgeDB │                 │
│  │ Azure OpenAI │  │  JSON Files  │                 │
│  └──────────────┘  └──────────────┘                 │
└─────────────────────────────────────────────────────┘
```

## Features

- 🚨 **Outage Analysis** — Describe the outage and get an instant AI-generated recovery plan
- 📋 **Dependency-Aware Steps** — Recovery steps ordered by service dependencies
- 💬 **Chat Interface** — Ask follow-up questions about the recovery plan
- 🗺️ **Dependency Map** — Visual service dependency panel
- 📚 **Knowledge Base** — Grounded in TSGs, RCAs, and service dependency data
- 🎭 **Demo Mode** — Works without AI API keys using a realistic mock plan

## Quick Start

### With Docker

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your Azure OpenAI credentials (optional)
docker-compose up --build
```

Visit http://localhost:5173

### Without Docker

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with credentials (optional)
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint | Optional |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Optional |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment name (default: `gpt-4o`) | Optional |
| `AZURE_OPENAI_API_VERSION` | API version (default: `2024-02-01`) | Optional |
| `OPENAI_API_KEY` | Standard OpenAI key (fallback) | Optional |

> **Note:** If no API key is configured, the app runs in **Demo Mode** with a realistic mock recovery plan.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/advisor/health` | Health check |
| `POST` | `/api/v1/advisor/analyze` | Analyze outage, return recovery plan |
| `POST` | `/api/v1/advisor/chat` | Follow-up chat message |

### Example: Analyze Outage
```bash
curl -X POST http://localhost:8000/api/v1/advisor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "description": "PilotFish-Core is crash-looping, health checks failing",
    "severity": "P1",
    "affected_services": ["PilotFish-Core", "PilotFish-API"]
  }'
```

## Running Tests

**Backend:**
```bash
cd backend && pytest tests/ -v
```

**Frontend:**
```bash
cd frontend && npm run test
```

## Knowledge Base

The advisor is grounded in structured knowledge in `backend/knowledge_base/`:

- **TSGs** (`tsgs/`) — Troubleshooting guides with recovery procedures
- **RCAs** (`rcas/`) — Post-incident reviews with lessons learned
- **Dependencies** (`dependencies/`) — Service dependency graph

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request
