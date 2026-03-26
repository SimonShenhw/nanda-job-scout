# 🎯 Job Scout AI — Web UI (Module C)

> Interactive Streamlit interface for the Job Scout AI multi-agent system.  
> **Course:** AAI 5025 | **University:** Northeastern University

---

## Overview

This module provides the **user-facing web interface** for the Job Scout AI platform. It connects to the backend agents (Job Scout Agent, Interview Prep Module) and presents results through an intuitive, professional UI.

### Features

- **Job Search Dashboard** — Enter location, keywords, and number of results to discover relevant tech internships
- **Resume Upload & Parsing** — Upload a PDF or TXT resume; the app extracts text automatically for personalized results
- **Interactive Job Cards** — View job listings with skill badges, company info, summaries, and direct apply links
- **AI Interview Prep Chat** — Select any job and generate tailored interview questions with a ChatGPT-like interface
- **Graceful Error Handling** — Automatic retry logic, input validation, and demo mode fallback when backend is unavailable
- **Connection Status Indicator** — Live server (green) vs demo mode (yellow) shown in sidebar

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit 1.x |
| PDF Parsing | PyPDF2 |
| HTTP Client | Requests |
| Data Display | Pandas |
| Styling | Custom CSS |
| Deployment | Docker + Linode |

---

## Quick Start

### Option 1: Local Development

```bash
# 1. Clone the repository
git clone <repo-url>
cd job-scout-ui

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`

### Option 2: Docker

```bash
# Build the image
docker build -t job-scout-ui .

# Run the container
docker run -p 8501:8501 job-scout-ui
```

---

## Project Structure

```
job-scout-ui/
├── .streamlit/
│   └── config.toml          # Streamlit theme configuration
├── app.py                   # Main Streamlit application
├── api_client.py            # API client with retry logic & mock data
├── style.css                # Custom CSS for professional styling
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container configuration
├── .dockerignore            # Docker build exclusions
└── README.md                # This file
```

---

## API Integration

This module communicates with two backend endpoints:

### 1. Job Scout Agent (Agent 1)

```
POST http://<server-ip>:8080/api/v1/scout
```

**Request:**
```json
{
  "location": "Greater Boston Area",
  "keywords": "Data Scientist AI Intern",
  "num_results": 3
}
```

**Response:**
```json
{
  "status": "success",
  "jobs": [
    {
      "company": "Wayfair",
      "job_title": "Data Science Intern",
      "core_skills": ["Python", "SQL", "ML"],
      "summary": "Build ML models for recommendations",
      "apply_link": "https://..."
    }
  ]
}
```

### 2. Interview Prep (Module B)

```
POST http://<server-ip>:8080/api/v1/interview
```

**Request:**
```json
{
  "job": { "company": "...", "job_title": "..." },
  "resume_text": "Extracted resume content..."
}
```

**Response:**
```json
{
  "status": "success",
  "questions": [
    "Tell me about a project where you used Python...",
    "How would you design a data pipeline...",
    "Walk me through how you would explain..."
  ]
}
```

---

## Configuration

To connect to the live backend, update `BASE_URL` in `api_client.py`:

```python
BASE_URL = "https://nanda-job-scout.onrender.com"
```

**Note:** The backend is hosted on Render's free tier. The first request after a period of inactivity may take up to 60 seconds while the server wakes up. Subsequent requests will be fast.

---

## Deployment on Linode

```bash
# 1. SSH into your Linode server
ssh root@<linode-ip>

# 2. Clone the repo
git clone <repo-url>
cd job-scout-ui

# 3. Build and run with Docker
docker build -t job-scout-ui .
docker run -d -p 8501:8501 --restart unless-stopped job-scout-ui
```

The UI will be accessible at `http://<linode-ip>:8501`

---

## Author

**Module C — Web UI (Streamlit)**  
AAI 5025 — Northeastern University