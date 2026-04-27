# Job Scout

An agentic AI job-discovery and interview-prep platform. Users upload a resume, enter a target role and preferred location, and receive matched job openings, tailored interview questions, and salary-vs-cost-of-living insights — all through a Streamlit dashboard backed by FastAPI agents and LangGraph orchestration.

---

## Architecture

```
Streamlit UI (frontend_ui · port 8501)
  ├─► POST /api/v1/scout  →  Agent 1 – Job Scout        (port 8080)
  │                            ├─► SerpAPI (Google Jobs web search)
  │                            └─► Google Gemini (structured extraction)
  │
  ├─► POST /api/v1/scout  →  Agent 3 – CostCompass       (port 8083)
  │   (job cards enriched)     ├─► Teleport API (12 US cities)
  │                            ├─► 50/30/20 budgeting rule
  │                            └─► Google Gemini (affordability comment)
  │
  └─► POST /api/v1/prep   →  Agent 2 – Interview Prep    (port 8081)
                               ├─► Resume parsing (PDF / DOCX / TXT)
                               ├─► ChromaDB (resume tips via Module A)
                               └─► Google Gemini (question generation)

module_a_vectordb  →  Semantic search over resume tips / interview guidance (ChromaDB · port 8000)
module_d_langgraph →  LangGraph orchestration across all agents (port 8082)
```

Each FastAPI agent exposes a NANDA-compatible agent card at `/.well-known/agent.json`.

---

## Modules

| Directory | Description |
|---|---|
| `agent1_scout/` | FastAPI service that searches for jobs via SerpAPI and structures results with Gemini. Runs on **port 8080**. |
| `agent2_questions/` | FastAPI service that parses a resume and generates tailored interview questions per job. Runs on **port 8081**. |
| `agent_b/` | CostCompass — FastAPI service that estimates monthly cost of living for 12 US cities and rates each job's salary as Comfortable / Moderate / Tight. Runs on **port 8083**. |
| `frontend_ui/` | Streamlit dashboard where users upload a resume, choose a job target and location, review matched openings, and practice interviews. |
| `module_a_vectordb/` | Builds a ChromaDB vector store from 20 structured interview-tip guidelines and serves semantic search via FastAPI on **port 8000**. |
| `module_d_langgraph/` | LangGraph orchestration service that chains Agent 1, Module A, Agent 2, and Agent 3 into a single master-graph workflow. Runs on **port 8082**. |
| `scripts/` | Utility scripts, including NANDA Index registration. |

---

## Agent Fact Cards (NANDA)

All three agents are registered in the [NANDA Index](https://index.projectnanda.org/) and [NANDA Registry](https://nanda-registry.com/). Each exposes a machine-readable agent card:

| Agent | Agent Card URL |
|---|---|
| Agent 1 – Job Scout | `http://<SCOUT_PUBLIC_URL>/.well-known/agent.json` |
| Agent 2 – Interview Prep | `http://<PREP_PUBLIC_URL>/.well-known/agent.json` |
| Agent 3 – CostCompass | `http://66.228.47.228:8083/.well-known/agent.json` |

Card templates are located at `agent1_scout/agent.json`, `agent2_questions/agent.json`, and `agent_b/agent.json`.

---

## Prerequisites

- Python 3.11 or 3.12 recommended
- A Google AI API key (`GOOGLE_API_KEY`)
- A SerpAPI key (`SERPAPI_API_KEY`)
- Docker Desktop or Docker Engine (for the full stack via Docker Compose)

---

## Environment Variables

Copy the template and fill in your keys:

```bash
cp example.env .env
```

| Variable | Required | Purpose |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | Google Gemini (all agents) |
| `SERPAPI_API_KEY` | Yes | Agent 1 job search |
| `NANDA_REGISTRY_URL` | NANDA registration | Target registry endpoint |
| `SCOUT_PUBLIC_URL` | NANDA registration | Public URL for Agent 1 |
| `PREP_PUBLIC_URL` | NANDA registration | Public URL for Agent 2 |

`SCOUT_PUBLIC_URL` and `PREP_PUBLIC_URL` must be internet-reachable if you plan to register with the NANDA Index.

---

## Quick Start with Docker

Run the full stack (Agents 1, 2, Module A, Module D, and the frontend):

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Agent 1 – Job Scout | http://127.0.0.1:8080 |
| Agent 2 – Interview Prep | http://127.0.0.1:8081 |
| Agent 3 – CostCompass (live) | http://66.228.47.228:8083 |
| Module A – Vector KB | http://127.0.0.1:8000 |
| Module D – LangGraph | http://127.0.0.1:8082 |
| Frontend | http://127.0.0.1:8501 |

The frontend container is automatically wired to the backend services:

```
SCOUT_API_URL=http://agent1-scout:8080
PREP_API_URL=http://agent2-questions:8081
```

Stop the stack:

```bash
docker compose down
```

---

## Manual Quick Start

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

Starts on `http://127.0.0.1:8080`.

Key endpoints:

- `GET  /health`
- `GET  /.well-known/agent.json`
- `POST /api/v1/scout`

Example request:

```bash
curl -X POST "http://127.0.0.1:8080/api/v1/scout" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Greater Boston Area",
    "keywords": "Data Scientist",
    "num_results": 3
  }'
```

Returns a list of `JobJD` objects: `job_title`, `company`, `location`, `link`, `skills[]`, `estimated_salary`, `description`.

### 3. Agent 3 — CostCompass

Deployed live at `http://66.228.47.228:8083`. To run locally:

```bash
pip install -r agent_b/requirements.txt
python agent_b/main.py
```

Key endpoints:

- `GET  /health`
- `GET  /.well-known/agent.json`
- `POST /api/v1/cost`

Agent 3 accepts a city and salary from Agent 1's output and appends:
- `monthly_cost_range` — estimated monthly living cost (e.g. `$2,890–$3,690/mo`)
- `affordability` — `Comfortable` / `Moderate` / `Tight` (50/30/20 rule)
- AI-generated one-sentence financial comment via Gemini

Frontend also available at `http://66.228.47.228:8501`.

### 4. Agent 2 — Interview Prep

```bash
pip install -r agent2_questions/requirements.txt
python agent2_questions/workflow.py
```

Starts on `http://127.0.0.1:8081`.

Key endpoints:

- `GET  /health`
- `GET  /.well-known/agent.json`
- `POST /api/v1/prep`

The agent runs a multi-step workflow: resume parsing → job analysis → fit analysis → prompt building → Gemini question generation → structured output.

### 5. Frontend

```bash
pip install -r frontend_ui/requirements.txt
streamlit run frontend_ui/app.py
```

To use local backends instead of deployed URLs:

```bash
export SCOUT_API_URL=http://127.0.0.1:8080
export PREP_API_URL=http://127.0.0.1:8081
streamlit run frontend_ui/app.py
```

### 6. Module A — Vector Knowledge Base (optional)

```bash
pip install -r module_a_vectordb/requirements.txt
python module_a_vectordb/build_db.py   # builds the ChromaDB store
python module_a_vectordb/main.py       # starts the FastAPI search service
```

Starts on `http://127.0.0.1:8000`.

Key endpoints:

- `GET  /health`
- `POST /api/v1/search` — semantic search over 20 structured interview-tip guidelines

Uses `all-MiniLM-L6-v2` (SentenceTransformers) for embeddings, `RecursiveCharacterTextSplitter` with `chunk_size=350` and `chunk_overlap=50`.

### 7. Module D — LangGraph Orchestrator

```bash
pip install -r module_d_langgraph/requirements.txt
python module_d_langgraph/main.py
```

Starts on `http://127.0.0.1:8082`.

Key endpoints:

- `GET  /health`
- `POST /api/v1/master-graph`

Module D coordinates all agents in a single call: Agent 1 (jobs) → Module A (resume tips) → Agent 2 (interview questions) → Agent 3 (cost of living). Returns a unified JSON response with per-service status fields. Includes fallback logic so the pipeline continues even if one agent is unavailable.

---

## NANDA Index Registration

Register all agents with the NANDA Index:

```bash
pip install -r scripts/requirements.txt
python scripts/register_with_nanda.py
```

Useful options:

```bash
python scripts/register_with_nanda.py --dry-run       # validate without submitting
python scripts/register_with_nanda.py --skip-health   # skip reachability check
python scripts/register_with_nanda.py --skip-verify   # skip post-submission verification
```

See also: `how_to_register_an_agent_fact_card_to_NANDA_index.txt`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit, PyPDF2, Pandas, Requests |
| Backend agents | FastAPI, Uvicorn, Pydantic |
| Orchestration | LangGraph |
| LLM | Google Gemini API |
| Web search | SerpAPI (Google Jobs) |
| Cost-of-living data | Teleport API |
| Vector search | ChromaDB, SentenceTransformers (MiniLM-L6-v2) |
| Agent discovery | NANDA Index / Registry (agent fact cards) |
| Deployment | Docker Compose, Linode (Agent 3) |
| Language | Python 3.11 / 3.12 |

---

## Live Deployments

| Component | URL |
|---|---|
| Agent 3 – CostCompass API | http://66.228.47.228:8083 |
| Agent 3 – CostCompass Frontend | http://66.228.47.228:8501 |

---

## Notes

- `.env` is gitignored — keep API keys local and never commit them.
- `.vscode/` is gitignored — use your own editor settings freely.
- Agent cards are served at `/.well-known/agent.json` and loaded from `agent.json` files in each agent directory.
- Module D's LangGraph graph is on the `Master_graph_integration` branch.

---

## Authors

| Name | Module |
|---|---|
| Haowei Shen | Agent 1 – Job Scout |
| Peter Adranly | Agent 2 – Interview Prep, Frontend, Overview |
| Wei Dong | Agent 3 – CostCompass |
| Fengbo Lyo | Module A – Vector Knowledge Base |
| Ishikaa Chawada | Module D – LangGraph Orchestrator |
| Zahra Joulaei | Frontend |

*Northeastern University · AAI 6600 · Spring 2025*
