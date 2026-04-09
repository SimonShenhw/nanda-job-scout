import json
import os
import requests
import time


SCOUT_API_URL = os.environ.get("SCOUT_API_URL", "http://127.0.0.1:8080").rstrip("/")
PREP_API_URL = os.environ.get("PREP_API_URL", "http://127.0.0.1:8081").rstrip("/")

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


def scout_jobs(location: str, keywords: str, num_results: int) -> dict:
    """
    Send a request to Agent 1 (Job Scout) and return structured job data.
    Falls back to mock data if the server is not available yet.
    """
    result = _request_with_retry(
        method="POST",
        url=f"{SCOUT_API_URL}/api/v1/scout",
        payload={
            "location": location,
            "keywords": keywords,
            "num_results": num_results,
        },
        timeout=90,  # Render free tier has slow cold starts
    )

    if result["status"] == "success":
        data = result["data"]
        return {"status": "success", "jobs": data.get("jobs", []), "is_live": True}

    # Fall back to mock data when the live service is unreachable or temporarily failing.
    mock = _mock_scout_response(num_results)
    mock["is_live"] = False
    mock["message"] = result.get("message", "Using demo data.")
    return mock


def generate_interview_questions(job: dict, resume_text: str) -> dict:
    """
    Send job + resume to Agent 2 and get tailored interview questions.
    Falls back to mock data if Module B is not available yet.
    """
    jobs_json = json.dumps({"jobs": [job]})
    files = {
        "resume": (
            "resume.txt",
            (resume_text or "Sample resume").encode("utf-8"),
            "text/plain",
        )
    }

    result = _request_with_retry(
        method="POST",
        url=f"{PREP_API_URL}/api/v1/prep",
        data={"jobs_json": jobs_json},
        files=files,
        timeout=60,
    )

    if result["status"] == "success":
        data = result["data"]
        questions = data.get("questions", [])
        if not questions and data.get("results"):
            questions = data["results"][0].get("questions", [])

        normalized_questions = [
            q.get("question", str(q)) if isinstance(q, dict) else str(q)
            for q in questions
        ]
        return {"status": "success", "questions": normalized_questions, "is_live": True}

    mock = _mock_interview_response(job)
    mock["is_live"] = False
    mock["message"] = result.get("message", "Using demo questions.")
    return mock


# ==============================================
# Mock data for development (remove when APIs are live)
# ==============================================

def _mock_scout_response(num_results: int) -> dict:
    mock_jobs = [
        {
            "company": "Wayfair",
            "job_title": "Data Science Intern",
            "core_skills": ["Python", "SQL", "Machine Learning"],
            "summary": "Build ML models for product recommendation engine",
            "apply_link": "https://wayfair.com/careers",
        },
        {
            "company": "HubSpot",
            "job_title": "AI Research Intern",
            "core_skills": ["Python", "NLP", "TensorFlow"],
            "summary": "Develop NLP features for marketing automation platform",
            "apply_link": "https://hubspot.com/careers",
        },
        {
            "company": "Toast",
            "job_title": "Data Engineer Intern",
            "core_skills": ["Python", "Spark", "SQL", "AWS"],
            "summary": "Build data pipelines for restaurant analytics platform",
            "apply_link": "https://toast.com/careers",
        },
        {
            "company": "DraftKings",
            "job_title": "ML Engineer Intern",
            "core_skills": ["Python", "PyTorch", "Docker"],
            "summary": "Create real-time prediction models for sports analytics",
            "apply_link": "https://draftkings.com/careers",
        },
        {
            "company": "Akamai",
            "job_title": "Data Analyst Intern",
            "core_skills": ["SQL", "Tableau", "Python"],
            "summary": "Analyze network performance data and build dashboards",
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