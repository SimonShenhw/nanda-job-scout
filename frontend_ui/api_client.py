import json
import os
import requests
import time


MODULE_D_API_URL = os.environ.get("MODULE_D_API_URL", "http://127.0.0.1:8082").rstrip("/")

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def _request_with_retry(
    method: str,
    url: str,
    payload: dict | None = None,
    data: dict | None = None,
    files: dict | None = None,
    timeout: int = 30,
) -> dict:
    """
    Generic request handler with retry logic and detailed error messages.
    Supports both JSON and multipart/form-data requests.
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            request_kwargs = {
                "method": method,
                "url": url,
                "timeout": timeout,
            }

            if files or data:
                request_kwargs["data"] = data or {}
                request_kwargs["files"] = files or {}
            else:
                request_kwargs["json"] = payload or {}

            response = requests.request(**request_kwargs)
            response.raise_for_status()
            return {"status": "success", "data": response.json()}

        except requests.exceptions.ConnectionError:
            last_error = "connection_error"
            # No point retrying if server is not reachable
            break

        except requests.exceptions.Timeout:
            last_error = "timeout"
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
            break

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 0
            if status_code == 429:
                last_error = "rate_limit"
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * 2)
                    continue
            elif status_code >= 500:
                last_error = "server_error"
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
            else:
                last_error = f"http_{status_code}"
            break

        except Exception as e:
            last_error = str(e)
            break

    # Map error types to user-friendly messages
    error_messages = {
        "connection_error": "Cannot reach the server. It may not be deployed yet — using demo data.",
        "timeout": "Server took too long to respond. Please try again.",
        "rate_limit": "Too many requests. Please wait a moment and try again.",
        "server_error": "The server encountered an error. Please try again later.",
    }

    friendly_msg = error_messages.get(
        last_error,
        f"An unexpected error occurred: {last_error}",
    )

    return {"status": "error", "error_type": last_error, "message": friendly_msg}


def _job_key(company: str, job_title: str) -> str:
    return f"{company.strip().lower()}::{job_title.strip().lower()}"


def _normalize_questions(question_items: list) -> list[str]:
    return [
        item.get("question", str(item)) if isinstance(item, dict) else str(item)
        for item in question_items
    ]


def _normalize_tips(raw_tips) -> list[str]:
    if isinstance(raw_tips, list):
        lines = [str(item) for item in raw_tips]
    else:
        lines = str(raw_tips or "").splitlines()

    return [
        line.lstrip("-• ").strip()
        for line in lines
        if line.strip()
    ]


def run_module_d_workflow(query: str, location: str, resume_text: str) -> dict:
    """
    Call Module D as the single orchestrator for jobs, resume tips, and
    interview questions, then adapt its response for the frontend UI.
    """
    result = _request_with_retry(
        method="POST",
        url=f"{MODULE_D_API_URL}/api/v1/master-graph",
        payload={
            "query": query,
            "location": location,
            "resume_text": resume_text or "Sample resume",
        },
        timeout=120,
    )

    if result["status"] != "success":
        return {
            "status": "error",
            "jobs": [],
            "job_prep": {},
            "service_statuses": {
                "agent1": {"status": "failed", "message": result.get("message", "Module D could not reach Agent 1.")},
                "agent2": {"status": "failed", "message": result.get("message", "Module D could not reach Agent 2.")},
                "module_a": {"status": "failed", "message": result.get("message", "Module D could not reach Module A.")},
                "agent3": {"status": "failed", "message": result.get("message", "Module D could not reach Agent 3.")},
            },
            "overall_status": "failed",
            "message": result.get("message", "Module D orchestration failed."),
            "is_live": False,
        }

    payload = result["data"]
    overall_status = payload.get("overall_status", "partial")
    services = payload.get("services", {})
    data = payload.get("data", {})

    jobs = data.get("jobs", [])
    tips = _normalize_tips(data.get("tips", ""))
    questions = _normalize_questions(data.get("questions", []))
    cost_of_living_analysis = data.get("cost_of_living_analysis", [])

    service_statuses = {
        "agent1": {
            "status": services.get("agent1_status", "unknown"),
            "message": services.get("agent1_error") or "Agent 1 returned live matched jobs.",
        },
        "agent2": {
            "status": services.get("module_b_status", "unknown"),
            "message": services.get("module_b_error") or "Agent 2 returned interview questions.",
        },
        "module_a": {
            "status": services.get("module_a_status", "unknown"),
            "message": services.get("module_a_error") or "Module A returned resume-tailoring tips.",
        },
        "agent3": {
            "status": services.get("agent3_status", "unknown"),
            "message": services.get("agent3_error") or "Agent 3 returned cost-of-living analysis.",
        },
    }

    cost_map = {
        _job_key(item.get("company", ""), item.get("job_title", "")): item
        for item in cost_of_living_analysis
        if isinstance(item, dict)
    }

    grouped_questions = [questions[i:i + 3] for i in range(0, len(questions), 3)] or [[]]
    job_prep = {}
    for index, job in enumerate(jobs):
        key = _job_key(job.get("company", ""), job.get("job_title", ""))
        job_prep[key] = {
            "candidate_highlights": [
                f"Module D matched this role for '{query}' in {location}.",
                "This result was produced through the orchestrated master graph.",
            ],
            "resume_tips": tips,
            "questions": grouped_questions[index] if index < len(grouped_questions) else questions[:3],
            "cost_of_living": cost_map.get(key, {}),
        }

    overall_message = {
        "success": "Module D completed successfully with live results from Agent 1, Module A, Agent 2, and Agent 3.",
        "partial": "Module D completed in partial/fallback mode. Some services returned demo or fallback content.",
        "failed": "Module D could not complete the full workflow.",
    }.get(overall_status, "Module D returned a response.")

    return {
        "status": "success",
        "jobs": jobs,
        "job_prep": job_prep,
        "service_statuses": service_statuses,
        "overall_status": overall_status,
        "message": overall_message,
        "is_live": overall_status == "success",
    }


# ==============================================
# Mock data for development (remove when APIs are live)
# ==============================================

def _mock_scout_response(num_results: int) -> dict:
    mock_jobs = [
        {
            "company": "Wayfair",
            "job_title": "Data Scientist",
            "estimated_salary": "$92k-$108k",
            "core_skills": ["Python", "SQL", "Machine Learning"],
            "summary": "Use applied ML and experimentation to improve marketplace recommendations.",
            "apply_link": "https://wayfair.com/careers",
        },
        {
            "company": "HubSpot",
            "job_title": "AI Product Analyst",
            "estimated_salary": "$88k-$102k",
            "core_skills": ["Python", "Analytics", "NLP"],
            "summary": "Translate customer and product data into AI-powered workflow improvements.",
            "apply_link": "https://hubspot.com/careers",
        },
        {
            "company": "Toast",
            "job_title": "Data Engineer",
            "estimated_salary": "$105k-$125k",
            "core_skills": ["Python", "Spark", "SQL", "AWS"],
            "summary": "Build reliable data pipelines and reporting systems for restaurant operations.",
            "apply_link": "https://toast.com/careers",
        },
        {
            "company": "DraftKings",
            "job_title": "Machine Learning Engineer",
            "estimated_salary": "$118k-$136k",
            "core_skills": ["Python", "PyTorch", "Docker"],
            "summary": "Develop predictive models and deploy them into real-time product experiences.",
            "apply_link": "https://draftkings.com/careers",
        },
        {
            "company": "Akamai",
            "job_title": "Business Intelligence Analyst",
            "estimated_salary": "$84k-$97k",
            "core_skills": ["SQL", "Tableau", "Python"],
            "summary": "Analyze operational data and create dashboards that drive business decisions.",
            "apply_link": "https://akamai.com/careers",
        },
    ]
    return {
        "status": "success",
        "jobs": mock_jobs[:num_results],
    }


def _mock_interview_response(job: dict) -> dict:
    title = job.get("job_title", "this role")
    company = job.get("company", "the company")
    return {
        "status": "success",
        "questions": [
            f"Tell me about a project where you used Python to solve a real data problem. How would that experience help you as a {title} at {company}?",
            f"How would you design a data pipeline that handles missing or messy data for {company}'s platform?",
            f"Walk me through how you would explain a complex ML model's predictions to a non-technical stakeholder at {company}.",
        ],
    }