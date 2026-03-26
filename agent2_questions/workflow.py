import os
import json
import asyncio
from copy import deepcopy
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List

# Resume parsing dependencies
import pdfplumber                          # pip install pdfplumber
from docx import Document as DocxDocument  # pip install python-docx
import io

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate


# ==========================================
# 1. Data Structures (A2A Protocol)
#    Mirrors Agent 1's ScoutResponse schema
#    so the JSON output slots in directly.
# ==========================================

class JobJD(BaseModel):
    """Mirrors Agent 1's JobJD — no changes needed for A2A compatibility."""
    company: str
    job_title: str
    core_skills: List[str]
    summary: str
    apply_link: str


class InterviewQuestion(BaseModel):
    category: str = Field(description="Question category: Technical | Behavioral | Role-Specific")
    question: str = Field(description="The tailored interview question")
    rationale: str = Field(description="Why this question was chosen given the resume and JD")


class InterviewPrepResponse(BaseModel):
    status: str
    company: str
    job_title: str
    candidate_highlights: List[str] = Field(description="Key resume strengths relevant to this JD")
    questions: List[InterviewQuestion]


class BatchInterviewPrepResponse(BaseModel):
    status: str
    results: List[InterviewPrepResponse]


# ==========================================
# 2. Resume Parsing Utilities
#    Supports .pdf, .docx, and .txt formats.
# ==========================================

def _parse_pdf(data: bytes) -> str:
    """Extract plain text from a PDF file using pdfplumber."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def _parse_docx(data: bytes) -> str:
    """Extract plain text from a .docx file."""
    doc = DocxDocument(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()


def _parse_txt(data: bytes) -> str:
    """Decode a plain-text resume; try UTF-8, fall back to latin-1."""
    try:
        return data.decode("utf-8").strip()
    except UnicodeDecodeError:
        return data.decode("latin-1").strip()


def extract_resume_text(filename: str, data: bytes) -> str:
    """
    Dispatch to the correct parser based on file extension.
    Raises ValueError for unsupported formats so FastAPI can surface a clean 400.
    """
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return _parse_pdf(data)
    elif ext == "docx":
        return _parse_docx(data)
    elif ext == "txt":
        return _parse_txt(data)
    else:
        raise ValueError(f"Unsupported file type: .{ext}. Please upload a .pdf, .docx, or .txt file.")


# ==========================================
# 3. Core Agent Logic
#    One coroutine per job — runs concurrently
#    via asyncio.gather() for low latency.
# ==========================================

async def generate_questions_for_job(
    job: JobJD,
    resume_text: str,
    llm_chain,
) -> InterviewPrepResponse:
    """
    Generate 3 tailored interview questions for a single job.
    Retries up to 3 times on LLM parse failure (mirrors Agent 1's pattern).
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result: InterviewPrepResponse = await llm_chain.ainvoke({
                "company":     job.company,
                "job_title":   job.job_title,
                "core_skills": ", ".join(job.core_skills),
                "summary":     job.summary,
                "resume":      resume_text,
            })
            return result
        except Exception as e:
            print(f"⚠️  Attempt {attempt + 1} for '{job.job_title}' @ {job.company} failed: {e}")
            if attempt == max_retries - 1:
                raise Exception(
                    f"LLM failed to generate questions for {job.job_title} @ {job.company} after {max_retries} attempts."
                ) from e
            await asyncio.sleep(1)

    raise RuntimeError("Retry loop exited without returning a response.")


async def run_interview_agent(
    jobs: List[JobJD],
    resume_text: str,
) -> BatchInterviewPrepResponse:
    """
    Entry point: concurrently processes every job from Agent 1's output.
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("Missing GOOGLE_API_KEY environment variable.")

    # --- LLM setup ---
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
    structured_llm = llm.with_structured_output(InterviewPrepResponse)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an expert technical recruiter and career coach.
Given a candidate's resume and a specific job description, your task is:
1. Identify the candidate's most relevant skills and experiences (candidate_highlights).
2. Generate exactly 3 interview questions — one Technical, one Behavioral, one Role-Specific.
   Each question must be tailored to BOTH the JD and the candidate's actual background.
3. For each question, include a short rationale explaining why it's relevant.

Be specific. Reference actual skills, projects, or experiences from the resume where possible.
If any field in the JD is 'Not Available', infer reasonable context from the rest."""
        ),
        (
            "human",
            """=== JOB DESCRIPTION ===
Company:     {company}
Role:        {job_title}
Core Skills: {core_skills}
Summary:     {summary}

=== CANDIDATE RESUME ===
{resume}

Generate the structured output now."""
        ),
    ])

    chain = prompt | structured_llm

    # --- Fan-out: run all jobs concurrently ---
    print(f"Agent 2 processing {len(jobs)} job(s) concurrently...")
    tasks = [generate_questions_for_job(job, resume_text, chain) for job in jobs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Separate successes from failures — never let one bad job kill the batch
    successful: List[InterviewPrepResponse] = []
    for job, result in zip(jobs, results):
        if isinstance(result, InterviewPrepResponse):
            successful.append(result)
        else:
            print(f"❌  Skipping '{job.job_title}' @ {job.company}: {result}")

    if not successful:
        raise Exception("All jobs failed to generate interview questions. Check your LLM API key and quota.")

    return BatchInterviewPrepResponse(status="success", results=successful)


# ==========================================
# 4. FastAPI Deployment Shell
# ==========================================

app = FastAPI(
    title="Interview Prep Agent API",
    description=(
        "MIT NANDA Sandbox — Agent 2. "
        "Ingests Agent 1's job JSON + a candidate resume, "
        "and returns 3 tailored interview questions per job."
    ),
    version="1.0.0",
)

# ==========================================
# NANDA Agent Card (/.well-known/agent.json)
# ==========================================

AGENT_CARD_PATH = Path(__file__).with_name("agent.json")
with AGENT_CARD_PATH.open("r", encoding="utf-8") as agent_card_file:
    AGENT_CARD_TEMPLATE = json.load(agent_card_file)


def get_agent_card() -> dict:
    agent_card = deepcopy(AGENT_CARD_TEMPLATE)
    agent_card["url"] = os.getenv("PUBLIC_URL", agent_card["url"])
    return agent_card


@app.get("/.well-known/agent.json", tags=["NANDA"])
async def agent_card():
    """NANDA Agent Fact Card — machine-readable metadata for agent discovery."""
    return get_agent_card()


@app.post(
    "/api/v1/prep",
    response_model=BatchInterviewPrepResponse,
    tags=["Interview Prep Agent"],
    summary="Generate tailored interview questions from Agent 1 output + resume",
)
async def api_generate_interview_questions(
    resume: UploadFile = File(
        ...,
        description="Candidate resume — accepts .pdf, .docx, or .txt"
    ),
    jobs_json: str = Form(
        ...,
        description=(
            "Agent 1's JSON output — either the full ScoutResponse object "
            "({status, jobs: [...]}) or just the jobs array ([...])."
        )
    ),
):
    # --- 1. Parse resume ---
    try:
        resume_bytes = await resume.read()
        if not resume.filename:
            raise HTTPException(status_code=400, detail="Uploaded file is missing a filename.")
        resume_text = extract_resume_text(resume.filename, resume_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse resume: {e}")

    if not resume_text:
        raise HTTPException(status_code=422, detail="Resume appears to be empty or unreadable.")

    # --- 2. Parse Agent 1 JSON (flexible: full object OR bare array) ---
    try:
        parsed = json.loads(jobs_json)
        # Accept both {"status": ..., "jobs": [...]} and plain [...]
        raw_jobs = parsed.get("jobs", parsed) if isinstance(parsed, dict) else parsed
        jobs = [JobJD(**j) for j in raw_jobs]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid jobs_json format: {e}")

    if not jobs:
        raise HTTPException(status_code=400, detail="No jobs found in jobs_json.")

    # --- 3. Run the agent ---
    try:
        response = await run_interview_agent(jobs, resume_text)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 5. Health Check
# ==========================================

@app.get("/health", tags=["Ops"])
async def health():
    return {"status": "ok", "agent": "interview-prep", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)  # Port 8081 keeps it separate from Agent 1 (8080)
