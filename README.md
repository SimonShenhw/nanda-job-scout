# nanda-job-scout

An AI-powered job-search and interview-prep platform. Users search for internship listings, upload a resume, and receive tailored interview questions — all through a Streamlit dashboard backed by LangChain agents.

## Architecture

```
Streamlit UI (frontend_ui)
  ├─► POST /api/v1/scout  →  Agent 1 – Job Scout   (port 8080)
  │                            ├─► SerpAPI (web search)
  │                            └─► Google Gemini (structured extraction)
  │
  └─► POST /api/v1/prep   →  Agent 2 – Interview Prep (port 8081)
                               ├─► Resume parsing (PDF / DOCX / TXT)
                               └─► Google Gemini (question generation)

module_a_vectordb  →  Semantic search over resume / interview tips (ChromaDB)
module_d_langgraph →  (placeholder — not yet implemented)
```

Each FastAPI agent also exposes a NANDA-compatible agent card at `/.well-known/agent.json`.

## Modules

| Directory | Description |
|---|---|
| `agent1_scout/` | FastAPI service that searches for jobs via SerpAPI and structures results with Gemini. Runs on **port 8080**. |
| `agent2_questions/` | FastAPI service that parses a resume and generates tailored interview questions per job. Runs on **port 8081**. |
| `frontend_ui/` | Streamlit dashboard for searching jobs, uploading resumes, and practicing interviews. |
| `module_a_vectordb/` | Builds a ChromaDB vector store from resume tips and serves semantic search via FastAPI. |
| `module_d_langgraph/` | Placeholder for a future LangGraph-based workflow. |
| `scripts/` | Utility scripts, including NANDA Index registration. |

## Prerequisites

- Python 3.11 or 3.12 recommended
- A Google AI API key (`GOOGLE_API_KEY`)
- A SerpAPI key (`SERPAPI_API_KEY`)
- Docker Desktop or Docker Engine, if you want to run the full stack with Docker Compose

## Environment variables

Copy the template and fill in your keys:

```bash
cp example.env .env
```

Required for core app behavior:

- `GOOGLE_API_KEY`
- `SERPAPI_API_KEY`

Used for NANDA Index registration:

- `NANDA_REGISTRY_URL`
- `SCOUT_PUBLIC_URL`
- `PREP_PUBLIC_URL`

`SCOUT_PUBLIC_URL` and `PREP_PUBLIC_URL` must be public, internet-reachable URLs if you plan to register the agents with the NANDA Index.

## Quick start with Docker

Run the full stack:

```bash
docker compose up --build
```

Services:

- Agent 1: `http://127.0.0.1:8080`
- Agent 2: `http://127.0.0.1:8081`
- Frontend: `http://127.0.0.1:8501`

The frontend container is wired automatically to the two backend services through:

- `SCOUT_API_URL=http://agent1-scout:8080`
- `PREP_API_URL=http://agent2-questions:8081`

Stop the stack with:

```bash
docker compose down
```

## Manual quick start

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Agent 1 — Job Scout

```bash
pip install -r agent1_scout/requirements.txt
python agent1_scout/main.py
```

The API starts on `http://127.0.0.1:8080`.

Key endpoints:

- `GET /health`
- `GET /.well-known/agent.json`
- `POST /api/v1/scout`

Example request:

```bash
curl -X POST "http://127.0.0.1:8080/api/v1/scout" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Greater Boston Area",
    "keywords": "Data Scientist AI Intern",
    "num_results": 3
  }'
```

### 3. Agent 2 — Interview Prep

```bash
pip install -r agent2_questions/requirements.txt
python agent2_questions/workflow.py
```

Runs on `http://127.0.0.1:8081`.

Key endpoints:

- `GET /health`
- `GET /.well-known/agent.json`
- `POST /api/v1/prep`

### 4. Frontend

```bash
pip install -r frontend_ui/requirements.txt
streamlit run frontend_ui/app.py
```

The frontend defaults to the deployed backend URLs.

To use local backends without Docker, set environment variables before starting Streamlit:

```bash
export SCOUT_API_URL=http://127.0.0.1:8080
export PREP_API_URL=http://127.0.0.1:8081
streamlit run frontend_ui/app.py
```

### 5. Vector DB (optional)

```bash
pip install -r module_a_vectordb/requirements.txt
python module_a_vectordb/build_db.py
python module_a_vectordb/main.py
```

## NANDA Index registration

Both agents expose NANDA-compatible agent cards from JSON-backed templates:

- `agent1_scout/agent.json`
- `agent2_questions/agent.json`

To register the agents with the NANDA Index:

```bash
pip install -r scripts/requirements.txt
python scripts/register_with_nanda.py
```

Useful options:

```bash
python scripts/register_with_nanda.py --dry-run
python scripts/register_with_nanda.py --skip-health
python scripts/register_with_nanda.py --skip-verify
```

Additional reference:

- `how_to_register_an_agent_fact_card_to_NANDA_index.txt`

## Notes

- `.env` is ignored by git and should stay local.
- `.vscode/` is gitignored — use your own editor settings freely.
- The agent cards are served at `/.well-known/agent.json` and loaded from `agent.json` files in each agent directory.