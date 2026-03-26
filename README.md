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

## Modules

| Directory | Description |
|---|---|
| `agent1_scout/` | FastAPI service that searches for jobs via SerpAPI and structures results with Gemini. Runs on **port 8080**. |
| `agent2_questions/` | FastAPI service that parses a resume and generates tailored interview questions per job. Runs on **port 8081**. |
| `frontend_ui/` | Streamlit dashboard for searching jobs, uploading resumes, and practicing interviews. |
| `module_a_vectordb/` | Builds a ChromaDB vector store from resume tips and serves semantic search via FastAPI. |
| `module_d_langgraph/` | Placeholder for a future LangGraph-based workflow. |

## Prerequisites

- Python 3.11 or 3.12 recommended
- A Google AI API key (`GOOGLE_API_KEY`)
- A SerpAPI key (`SERPAPI_API_KEY`)

## Quick start

### 1. Environment variables

Copy the template and fill in your keys:

```bash
cp example.env .env
```

### 2. Agent 1 — Job Scout

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r agent1_scout/requirements.txt
python agent1_scout/main.py
```

The API starts on `http://127.0.0.1:8080` (docs at `/docs`).

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

Runs on `http://127.0.0.1:8081` (docs at `/docs`).

### 4. Vector DB (optional)

```bash
pip install -r module_a_vectordb/requirements.txt
python module_a_vectordb/build_db.py   # one-time: build the ChromaDB store
python module_a_vectordb/main.py       # serve the search API
```

### 5. Frontend

```bash
pip install -r frontend_ui/requirements.txt
streamlit run frontend_ui/app.py
```

> **Note:** The frontend defaults to the deployed backend URL. To use local backends, update `BASE_URL` in `frontend_ui/api_client.py`.

## Notes

- `.env` is ignored by git and should stay local.
- `.vscode/` is gitignored — use your own editor settings freely.