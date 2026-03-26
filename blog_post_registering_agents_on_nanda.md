# How We Registered Our AI Agents on the NANDA Network (And How You Can Too)

*A practical, step-by-step walkthrough for developers who want to make their AI agents discoverable on Project NANDA's "Internet of AI Agents."*

---

## The Problem: Your Agent Exists, But Nobody Knows About It

You've built an AI agent. Maybe it searches for jobs, generates interview questions, analyzes data, or does something else entirely. It runs on your server, it has an API, and it works great.

But it's invisible. No other agent on the internet knows it exists. If someone builds an AI orchestrator that needs job search capabilities, they have no way to discover your agent — they'd have to manually find your GitHub repo, read your docs, and hardcode your URL.

**Project NANDA** is trying to solve this. Built at MIT, NANDA (Networked AI Agents in Decentralized Architecture) is building the foundational infrastructure for an **open agentic web** — where AI agents can discover each other, verify capabilities, and coordinate tasks without human intervention.

The centerpiece is the **NANDA Index**: a registry where agents register themselves with metadata ("Agent Fact Cards") so other agents can find them by searching for capabilities. Think of it as DNS for AI agents.

The problem? The documentation for actually *doing* this is scattered across multiple repos, and the existing tooling (NEST framework, nanda-adapter) assumes you're building agents from scratch using their stack. If you already have a FastAPI/Flask/Express agent and just want to register it — the path isn't obvious.

This post documents exactly what we did.

---

## What We're Working With

Our project, **nanda-job-scout**, has two agents:

1. **Job Scout Agent** (port 8080) — Takes a location + keywords, searches the web via SerpAPI, and uses Google Gemini to extract structured job descriptions.
2. **Interview Prep Agent** (port 8081) — Takes those job descriptions plus a candidate's resume, and generates tailored interview questions.

Both are FastAPI applications. We wanted to register them on the NANDA Index so other agents on the network could discover and use them.

---

## Step 1: Understand the NANDA Index API

After digging through the [nanda-index](https://github.com/projnanda/nanda-index), [NEST](https://github.com/projnanda/NEST), and [adapter](https://github.com/projnanda/adapter) repositories, here's what we learned:

The NANDA Index is a **Flask application** (in [registry.py](https://github.com/projnanda/nanda-index/blob/main/registry.py)) backed by MongoDB. It runs at `https://registry.chat39.com:6900` and provides a REST API.

The two key endpoints for registration are:

### `POST /register`

Creates an agent record. Payload:

```json
{
  "agent_id": "your-unique-agent-id",
  "agent_url": "https://your-public-url.com",
  "api_url": "https://your-public-url.com"
}
```

The `agent_url` is what other agents use to reach yours. The `api_url` is the client-facing API URL (often the same). You can optionally include `agent_facts_url` — a URL pointing to your Agent Fact Card JSON.

### `PUT /agents/<agent_id>/status`

Enriches the agent record with capabilities and tags:

```json
{
  "alive": true,
  "capabilities": ["job-search", "llm-extraction"],
  "tags": ["career", "ai-recruiter"]
}
```

This is important because the `/search` endpoint lets other agents find you by capability.

That's it. Registration is just two HTTP calls. No special SDK or protocol required.

---

## Step 2: Add Agent Fact Card Endpoints

An "Agent Fact Card" is a JSON document that describes your agent — name, capabilities, input/output schemas, version, etc. It's served at `/.well-known/agent.json`, following the convention used by the Google A2A protocol.

Here's what we added to our FastAPI app:

```python
AGENT_CARD = {
    "name": "Job Scout Agent",
    "description": (
        "AI-powered job search agent that finds and extracts "
        "structured job descriptions from web search results."
    ),
    "url": os.getenv("PUBLIC_URL", "http://localhost:8080"),
    "version": "2.3.0",
    "capabilities": [
        "job-search",
        "web-scraping",
        "llm-extraction",
        "structured-output",
    ],
    "endpoints": {
        "scout": "/api/v1/scout",
        "health": "/health",
        "agent_card": "/.well-known/agent.json",
    },
    "input_schema": {
        "location": "string",
        "keywords": "string",
        "num_results": "int 1-10",
    },
    "output_schema": {
        "status": "string",
        "jobs": "array of {company, job_title, estimated_salary, ...}",
    },
    "provider": {
        "organization": "MIT NANDA Sandbox",
        "project": "nanda-job-scout",
    },
}


@app.get("/.well-known/agent.json", tags=["NANDA"])
async def agent_card():
    """NANDA Agent Fact Card."""
    return AGENT_CARD
```

**Key design decisions:**
- There's no enforced schema. We included fields that seemed useful for both human and machine consumers.
- The `capabilities` array mirrors what we'll register with the NANDA Index, so there's one source of truth.
- We included `input_schema` and `output_schema` so other agents (or LLM orchestrators) can understand how to call us without reading our docs.

---

## Step 3: Write the Registration Script

We wrote a standalone `scripts/register_with_nanda.py` that handles the full registration flow:

1. **Health check** — Verify the registry is reachable
2. **Verify agent cards** — Hit each agent's `/.well-known/agent.json` to confirm it's up
3. **Register** — `POST /register` to create the record
4. **Enrich** — `PUT /agents/<id>/status` to add capabilities and tags

The script reads configuration from environment variables:

```bash
# Set your agent's public URLs
export SCOUT_PUBLIC_URL=https://abc123.ngrok-free.app
export PREP_PUBLIC_URL=https://def456.ngrok-free.app

# Run registration
python scripts/register_with_nanda.py
```

It also supports `--dry-run` to preview payloads without sending, which is invaluable for debugging.

### Why not use nanda-adapter or NEST?

The [nanda-adapter](https://github.com/projnanda/adapter) library (`pip install nanda-adapter`) is designed for building agents from scratch using its `NANDA` class with a message improvement pipeline and Anthropic Claude. The [NEST](https://github.com/projnanda/NEST) framework similarly wraps everything in its own `A2AServer` bridge with `python_a2a`.

Both are great if you're starting fresh. But our agents already exist as FastAPI applications with their own LLM pipelines (Google Gemini + LangChain). We wanted to register — not rewrite.

Since the NANDA Index is just a REST API, we went direct with `requests`. The full registration logic is ~30 lines of Python.

---

## Step 4: Make Your Agent Publicly Reachable

The NANDA Index stores your agent's public URL. Other agents will use that URL to communicate with yours. So `http://localhost:8080` won't work.

For development, **ngrok** is the easiest option:

```bash
# Terminal 1: Start your agent
uvicorn agent1_scout.main:app --host 0.0.0.0 --port 8080

# Terminal 2: Create a public tunnel
ngrok http 8080
# → Forwarding: https://abc123.ngrok-free.app -> http://localhost:8080
```

Set the ngrok URL as `SCOUT_PUBLIC_URL` and register. For production, deploy to a cloud provider with a stable URL.

---

## Step 5: Verify

After registration, verify your agent is discoverable:

```bash
# Look up by ID
curl -k https://registry.chat39.com:6900/lookup/nanda-job-scout

# Search by capability
curl -k 'https://registry.chat39.com:6900/search?capabilities=job-search'

# List all agents
curl -k https://registry.chat39.com:6900/list
```

You should see your agent in the results, complete with the capabilities and tags you set.

---

## The Full Picture

Here's what the flow looks like end-to-end:

```
┌───────────────────────────────────────────────────────────┐
│                   Your Agent (FastAPI)                     │
│                                                           │
│  GET /.well-known/agent.json  →  Agent Fact Card (JSON)   │
│  POST /api/v1/scout           →  Your actual API          │
│  GET /health                  →  Health check             │
└───────────┬───────────────────────────────────────────────┘
            │
            │ register_with_nanda.py
            │   1. POST /register (agent_id, agent_url, api_url)
            │   2. PUT /agents/<id>/status (capabilities, tags)
            ▼
┌───────────────────────────────────────────────────────────┐
│              NANDA Index (registry.chat39.com:6900)        │
│                                                           │
│  Stores: agent_id, agent_url, api_url, capabilities,     │
│          tags, alive status, agent_facts_url              │
│                                                           │
│  Other agents query:                                      │
│    GET /search?capabilities=job-search                    │
│    → finds your agent → calls your API                    │
└───────────────────────────────────────────────────────────┘
```

---

## What We Learned

1. **The NANDA Index is simpler than it looks.** Under the hood it's a Flask app with MongoDB. Registration is two HTTP calls. Don't be intimidated by the NEST/adapter frameworks — they add A2A protocol support, but the registry itself is plain REST.

2. **Agent Fact Cards have no enforced schema.** This is both freeing and confusing. We looked at how NEST registers agents and modeled our cards similarly, but you can include whatever fields make sense for your agent.

3. **The `/.well-known/agent.json` convention matters.** While not required by the registry, serving your agent card at a well-known URL means clients can discover your capabilities without hitting the registry. It's like `robots.txt` for AI agents.

4. **You don't need the full A2A protocol to participate.** The NEST and adapter repos use `python_a2a` for agent-to-agent messaging (a specific message format with roles, conversations, etc.). But the registry doesn't care about your communication protocol — it just stores your URL. Other agents might call your REST API directly.

5. **Public URLs are the hard part.** The technical registration takes 5 minutes. Getting a stable, publicly-reachable URL for your agent is the actual deployment challenge. For development, ngrok works. For production, you need proper infrastructure.

---

## Resources

- **Our code:** [github.com/SimonShenhw/nanda-job-scout](https://github.com/SimonShenhw/nanda-job-scout) — see `scripts/register_with_nanda.py` and the `/.well-known/agent.json` endpoints
- **NANDA Index:** [github.com/projnanda/nanda-index](https://github.com/projnanda/nanda-index) — the registry source code
- **NEST framework:** [github.com/projnanda/NEST](https://github.com/projnanda/NEST) — full agent deployment framework (if you want the A2A protocol layer)
- **NANDA Adapter:** [github.com/projnanda/adapter](https://github.com/projnanda/adapter) — `pip install nanda-adapter` for building agents from scratch
- **Project NANDA:** [github.com/projnanda](https://github.com/projnanda) — the umbrella organization

---

*This post was written as part of the MIT NANDA Sandbox project. If you're attempting the same integration and hit issues, open a GitHub issue on our repo — we're happy to help.*
