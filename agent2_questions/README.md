# Agent 2 - Interview Prep Agent

## Overview

`workflow.py` is the core engine of Agent 2, an **Interview Preparation Engine** that generates tailored interview questions based on job descriptions and candidate resumes. This document outlines the architecture and key components that power the system.

### Quick Component Summary

| Component | Purpose |
|-----------|---------|
| **Data Structures** | Pydantic models for type-safe data handling (JobJD, InterviewQuestion, responses) |
| **Resume Parsing** | Multi-format resume extraction (.pdf, .docx, .txt) |
| **Core Agent Logic** | Concurrent LLM-powered interview question generation with retry logic |
| **FastAPI Deployment** | REST API endpoints for integration with Agent 1 and clients |
| **Health Checks** | Operational monitoring and service health verification |

---

## Workflow.py Architecture and Components

### Data Structures
Workflow.py utilizes a set of data structures designed to efficiently handle data related to job candidates and resumes. Key structures include:

- **JobJD**: Represents a job description from Agent 1, containing company, job title, core skills, summary, and apply link
- **InterviewQuestion**: Encapsulates a single interview question with category (Technical/Behavioral/Role-Specific), the question text, and rationale
- **InterviewPrepResponse**: Response for a single job, including candidate highlights and 3 tailored questions
- **BatchInterviewPrepResponse**: Aggregates responses for multiple jobs in a single batch

### Resume Parsing
The resume parsing component is responsible for extracting relevant information from various resume formats. This process includes:

- **PDF Parsing** (`_parse_pdf`): Uses `pdfplumber` to extract text from PDF documents page-by-page
- **DOCX Parsing** (`_parse_docx`): Uses `python-docx` to extract paragraphs from Word documents
- **TXT Parsing** (`_parse_txt`): Decodes plain-text resumes with UTF-8 and latin-1 fallback support
- **Format Dispatch** (`extract_resume_text`): Automatically routes to the correct parser based on file extension and raises clean errors for unsupported formats

### Core Agent Logic
The core agent logic is the heart of workflow.py, responsible for:

- **Job-Level Processing** (`generate_questions_for_job`): Generates 3 interview questions for a single job with 3-attempt retry logic
- **Batch Orchestration** (`run_interview_agent`): Entry point that manages concurrent processing of multiple jobs using `asyncio.gather()`
- **LLM Integration**: Utilizes Google Generative AI (`gemini-2.5-flash`) with structured output to ensure type-safe responses
- **Fault Tolerance**: One failed job doesn't crash the batch; failed jobs are logged and excluded from results
- **Prompt Engineering**: System prompt instructs the LLM to tailor questions to both JD and candidate background with specific rationales

### FastAPI Deployment
This component deals with exposing the agent's functionalities via a RESTful API using FastAPI:

- **Main Endpoint** (`POST /api/v1/prep`): Accepts resume file + jobs JSON, returns interview prep responses
- **Agent Discovery** (`GET /.well-known/agent.json`): Serves NANDA-compliant agent metadata for ecosystem discovery
- **Health Check** (`GET /health`): Operational monitoring endpoint returning agent status and version
- **Asynchronous Processing**: Leveraging FastAPI's async capabilities for efficient handling of multiple concurrent requests
- **Validation**: Input validation enforces file format support and JSON schema compliance

### Health Checks
The health check module ensures that the various components are functioning as expected:

- **Endpoint Monitoring** (`GET /health`): Simple health check returning status, agent name, and version
- **Error Handling**: Graceful error responses with appropriate HTTP status codes (400, 422, 500)
- **Logging**: Debug output for retry attempts and job failures to aid troubleshooting
- **Resource Management**: Proper async/await patterns prevent resource leaks during concurrent processing

---

## Integration with NANDA Ecosystem

- **A2A Protocol Compatibility**: Data models mirror Agent 1's JobJD for seamless data flow
- **Agent Card Discovery**: Published at `/.well-known/agent.json` for ecosystem agents to discover and integrate
- **Flexible JSON Input**: Accepts both full ScoutResponse objects and bare job arrays from Agent 1

---

## Technical Stack

- **Framework**: FastAPI + Uvicorn
- **Async Runtime**: Python asyncio
- **LLM**: Google Generative AI (Gemini 2.5 Flash)
- **Resume Parsing**: pdfplumber, python-docx
- **Type Safety**: Pydantic BaseModel
- **Port**: 8081 (separate from Agent 1's 8080)