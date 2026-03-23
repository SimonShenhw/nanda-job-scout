# nanda-job-scout

## Local setup

This repository currently contains a FastAPI backend in `agent1_scout` and an empty `frontend_ui` placeholder.

### Prerequisites

- Python 3.11 or 3.12 recommended
- A Google AI API key
- A SerpAPI key

### Environment variables

Copy the template and fill in your keys:

```bash
cp example.env .env
```

Required variables:

- `GOOGLE_API_KEY`
- `SERPAPI_API_KEY`

The backend loads the repo-root `.env` automatically.

### Install and run

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r agent1_scout/requirements.txt
python agent1_scout/main.py
```

The API starts on `http://127.0.0.1:8080`.

Interactive docs are available at `http://127.0.0.1:8080/docs`.

### Example request

```bash
curl -X POST "http://127.0.0.1:8080/api/v1/scout" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Greater Boston Area",
    "keywords": "Data Scientist AI Intern Wayfair Hubspot",
    "num_results": 3
  }'
```

### Notes

- `.env` is ignored by git and should stay local.
- If you are on Python 3.14, LangChain may emit a compatibility warning through its Pydantic v1 path.