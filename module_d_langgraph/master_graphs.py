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
    cost_of_living_analysis: list

    agent1_status: str
    module_a_status: str
    module_b_status: str
    agent3_status: str

    agent1_error: Optional[str]
    module_a_error: Optional[str]
    module_b_error: Optional[str]
    agent3_error: Optional[str]


if os.getenv("DOCKER_ENV"):
    AGENT1_URL = "http://agent1-scout:8080/api/v1/scout"
    MODULE_A_URL = "http://module-a-vectordb:8000/api/v1/search"
    MODULE_B_URL = "http://agent2-questions:8081/api/v1/prep"
else:
    AGENT1_URL = "http://127.0.0.1:8080/api/v1/scout"
    MODULE_A_URL = "http://127.0.0.1:8000/api/v1/search"
    MODULE_B_URL = "http://127.0.0.1:8081/api/v1/prep"

AGENT3_URL = os.getenv("AGENT3_URL", "").strip()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")


def _parse_salary_to_annual(salary_text: str | None):
    if not salary_text:
        return None

    salary_lower = salary_text.lower()
    if salary_lower == "not specified":
        return None

    values = [float(v.replace(",", "")) for v in __import__("re").findall(r"(\d[\d,]*(?:\.\d+)?)", salary_text)]
    if not values:
        return None

    if "k" in salary_lower and max(values) <= 500:
        values = [v * 1000 for v in values]

    annual_salary = sum(values) / len(values)
    if any(token in salary_lower for token in ["/hr", "per hour", "hour"]):
        annual_salary *= 2080
    elif annual_salary < 1000:
        annual_salary *= 1000

    return annual_salary


def _cost_of_living_index(location_name: str | None) -> int:
    location_lower = (location_name or "").lower()
    reference = {
        "new york": 95,
        "san francisco": 100,
        "seattle": 82,
        "boston": 80,
        "los angeles": 88,
        "austin": 62,
        "chicago": 70,
        "atlanta": 58,
        "dallas": 57,
        "miami": 74,
    }

    for city, score in reference.items():
        if city in location_lower:
            return score

    return 68


def _local_cost_of_living_analysis(jobs: list, location_name: str | None) -> list:
    analyses = []
    cost_index = _cost_of_living_index(location_name)
    baseline_cost = 38000 + (cost_index * 650)

    for job in jobs:
        salary_text = job.get("estimated_salary", "Not Specified")
        annual_salary = _parse_salary_to_annual(salary_text)

        if annual_salary is None:
            score = None
            label = "Salary unavailable"
            recommendation = "No salary was provided, so this affordability estimate is limited."
        else:
            raw_score = int((annual_salary / baseline_cost) * 55)
            score = max(1, min(100, raw_score))
            if score >= 80:
                label = "Excellent fit"
            elif score >= 60:
                label = "Solid fit"
            elif score >= 40:
                label = "Manageable"
            else:
                label = "Tight budget"
            recommendation = f"{label} for {location_name or 'this location'} based on the estimated salary."

        analyses.append(
            {
                "company": job.get("company", "Unknown Company"),
                "job_title": job.get("job_title", "Unknown Role"),
                "estimated_salary": salary_text,
                "annual_salary_estimate": round(annual_salary, 2) if annual_salary is not None else None,
                "cost_of_living_index": cost_index,
                "affordability_score": score,
                "label": label,
                "recommendation": recommendation,
            }
        )

    return analyses


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
            timeout=60,
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
        response = requests.post(MODULE_A_URL, json=payload, timeout=30)
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
        response = requests.post(MODULE_B_URL, data=form_data, files=files, timeout=60)

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


def evaluate_cost_of_living(state: GraphState):
    jobs = state.get("jobs", [])
    location_name = state.get("location", "Boston")

    if AGENT3_URL:
        try:
            response = requests.post(
                AGENT3_URL,
                json={
                    "location": location_name,
                    "jobs": jobs,
                },
                timeout=45,
            )
            response.raise_for_status()
            data = response.json()
            analyses = data.get("results") or data.get("cost_of_living_analysis") or data.get("data") or []
            if isinstance(analyses, list) and analyses:
                return {
                    "cost_of_living_analysis": analyses,
                    "agent3_status": "success",
                    "agent3_error": None,
                }
        except Exception as exc:
            local_analysis = _local_cost_of_living_analysis(jobs, location_name)
            return {
                "cost_of_living_analysis": local_analysis,
                "agent3_status": "fallback",
                "agent3_error": f"Agent 3 call failed; local cost-of-living analysis used. {exc}",
            }

    return {
        "cost_of_living_analysis": _local_cost_of_living_analysis(jobs, location_name),
        "agent3_status": "success",
        "agent3_error": None,
    }


def build_graph():
    logger.info("Building Module D master graph")
    builder = StateGraph(GraphState)

    builder.add_node("fetch_jobs", fetch_jobs)
    builder.add_node("fetch_tips", fetch_resume_tips)
    builder.add_node("generate_questions", generate_interview_questions)
    builder.add_node("evaluate_cost_of_living", evaluate_cost_of_living)

    builder.set_entry_point("fetch_jobs")
    builder.add_edge("fetch_jobs", "fetch_tips")
    builder.add_edge("fetch_tips", "generate_questions")
    builder.add_edge("generate_questions", "evaluate_cost_of_living")
    builder.set_finish_point("evaluate_cost_of_living")

    return builder.compile()
