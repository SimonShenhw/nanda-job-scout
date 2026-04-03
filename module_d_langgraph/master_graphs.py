from pathlib import Path
from typing import Optional, TypedDict
import json
import logging
import os

import requests
from dotenv import load_dotenv
from langgraph.graph import StateGraph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class GraphState(TypedDict):
    query: str
    location: Optional[str]
    resume_text: str

    jobs: list
    tips: str
    questions: list

    agent1_status: str
    module_a_status: str
    module_b_status: str

    agent1_error: Optional[str]
    module_a_error: Optional[str]
    module_b_error: Optional[str]


if os.getenv("DOCKER_ENV"):
    AGENT1_URL = "http://agent1-scout:8080/api/v1/scout"
    MODULE_A_URL = "http://module-a-vectordb:8000/api/v1/search"
    MODULE_B_URL = "http://agent2-questions:8081/api/v1/prep"
else:
    AGENT1_URL = "http://127.0.0.1:8080/api/v1/scout"
    MODULE_A_URL = "http://127.0.0.1:8000/api/v1/search"
    MODULE_B_URL = "http://127.0.0.1:8081/api/v1/prep"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")


def _build_agent1_headers() -> dict:
    # Agent1 currently reads keys from env; these headers are forwarded for compatibility.
    headers = {}
    if GOOGLE_API_KEY:
        headers["X-GOOGLE-API-KEY"] = GOOGLE_API_KEY
    if SERPAPI_API_KEY:
        headers["X-SERPAPI-API-KEY"] = SERPAPI_API_KEY
    return headers


def _normalize_jobs_for_agent2(jobs: list) -> list:
    normalized = []
    for job in jobs:
        if not isinstance(job, dict):
            continue

        core_skills = job.get("core_skills") or job.get("skills") or []
        if not isinstance(core_skills, list):
            core_skills = [str(core_skills)]

        normalized.append(
            {
                "company": job.get("company", "Unknown Company"),
                "job_title": job.get("job_title") or job.get("title") or "Unknown Role",
                "core_skills": core_skills,
                "summary": job.get("summary") or f"Role in {job.get('location', 'N/A')}",
                "apply_link": job.get("apply_link") or "Not Available",
            }
        )
    return normalized


def fetch_jobs(state: GraphState):
    payload = {
        "location": state.get("location", "Boston"),
        "keywords": state["query"],
        "num_results": 3,
    }

    try:
        response = requests.post(
            AGENT1_URL,
            json=payload,
            headers=_build_agent1_headers(),
            timeout=15,
        )
        response.raise_for_status()
        jobs = response.json().get("jobs", [])
        return {
            "jobs": jobs,
            "agent1_status": "success",
            "agent1_error": None,
        }
    except Exception as exc:
        fallback_jobs = [
            {
                "company": "TechCorp",
                "job_title": "AI Engineer",
                "core_skills": ["Python", "ML"],
                "summary": "Build and deploy ML features for products.",
                "apply_link": "Not Available",
            },
            {
                "company": "DataCo",
                "job_title": "ML Specialist",
                "core_skills": ["TensorFlow", "PyTorch"],
                "summary": "Design experiments and optimize model performance.",
                "apply_link": "Not Available",
            },
        ]

        error_detail = str(exc)
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            try:
                detail_json = exc.response.json()
                error_detail = detail_json.get("detail", error_detail)
            except Exception:
                error_detail = exc.response.text or error_detail

        return {
            "jobs": fallback_jobs,
            "agent1_status": "fallback",
            "agent1_error": f"Agent1 call failed; fallback data used. {error_detail}",
        }


def fetch_resume_tips(state: GraphState):
    payload = {
        "query": state["query"],
        "top_k": 3,
    }

    try:
        response = requests.post(MODULE_A_URL, json=payload, timeout=15)
        response.raise_for_status()
        tips = response.json().get("result", "")
        return {
            "tips": tips,
            "module_a_status": "success",
            "module_a_error": None,
        }
    except Exception:
        fallback_tips = (
            "- Highlight role-specific keywords\n"
            "- Quantify impact with metrics\n"
            "- Keep project summaries concise"
        )
        return {
            "tips": fallback_tips,
            "module_a_status": "fallback",
            "module_a_error": "Module A call failed; fallback tips used",
        }


def generate_interview_questions(state: GraphState):
    jobs = _normalize_jobs_for_agent2(state.get("jobs", []))
    resume_text = state.get("resume_text", "Sample resume")

    files = {
        "resume": ("resume.txt", resume_text, "text/plain"),
    }
    form_data = {
        "jobs_json": json.dumps({"jobs": jobs}),
    }

    try:
        response = requests.post(MODULE_B_URL, data=form_data, files=files, timeout=20)

        response.raise_for_status()
        data = response.json()

        if "questions" in data:
            questions = data.get("questions", [])
        else:
            questions = []
            for item in data.get("results", []):
                questions.extend(item.get("questions", []))

        return {
            "questions": questions,
            "module_b_status": "success",
            "module_b_error": None,
        }
    except Exception as exc:
        fallback_questions = [
            "Tell me about a project where you solved a difficult technical problem.",
            "How would you prioritize tasks under a tight deadline?",
            "Which skills from your resume best match this role and why?",
        ]

        error_detail = str(exc)
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            try:
                detail_json = exc.response.json()
                error_detail = detail_json.get("detail", error_detail)
            except Exception:
                error_detail = exc.response.text or error_detail

        return {
            "questions": fallback_questions,
            "module_b_status": "fallback",
            "module_b_error": f"Module B call failed; fallback questions used. {error_detail}",
        }


def build_graph():
    logger.info("Building Module D master graph")
    builder = StateGraph(GraphState)

    builder.add_node("fetch_jobs", fetch_jobs)
    builder.add_node("fetch_tips", fetch_resume_tips)
    builder.add_node("generate_questions", generate_interview_questions)

    builder.set_entry_point("fetch_jobs")
    builder.add_edge("fetch_jobs", "fetch_tips")
    builder.add_edge("fetch_tips", "generate_questions")
    builder.set_finish_point("generate_questions")

    return builder.compile()
