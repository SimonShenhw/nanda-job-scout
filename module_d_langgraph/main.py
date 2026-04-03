from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from master_graphs import build_graph

app = FastAPI(title="Module D: LangGraph Master Graph", version="1.0.0")

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


class MasterGraphRequest(BaseModel):
    query: str
    location: str = "Boston"
    resume_text: str = "Sample resume"


class ServiceStatus(BaseModel):
    agent1_status: str
    module_a_status: str
    module_b_status: str
    agent1_error: Optional[str] = None
    module_a_error: Optional[str] = None
    module_b_error: Optional[str] = None


class MasterGraphResponse(BaseModel):
    overall_status: str
    services: ServiceStatus
    data: dict


def _run_master_graph(request: MasterGraphRequest) -> MasterGraphResponse:
    graph = get_graph()

    initial_state = {
        "query": request.query,
        "location": request.location,
        "resume_text": request.resume_text,
        "jobs": [],
        "tips": "",
        "questions": [],
        "agent1_status": "pending",
        "module_a_status": "pending",
        "module_b_status": "pending",
        "agent1_error": None,
        "module_a_error": None,
        "module_b_error": None,
    }

    result = graph.invoke(initial_state)

    all_real = all(
        [
            result.get("agent1_status") == "success",
            result.get("module_a_status") == "success",
            result.get("module_b_status") == "success",
        ]
    )
    required_ok = all(
        [
            result.get("agent1_status") in ["success", "fallback"],
            result.get("module_a_status") in ["success", "fallback"],
            result.get("module_b_status") in ["success", "fallback"],
        ]
    )

    if all_real:
        overall_status = "success"
    elif required_ok:
        overall_status = "partial"
    else:
        overall_status = "failed"

    return MasterGraphResponse(
        overall_status=overall_status,
        services=ServiceStatus(
            agent1_status=result.get("agent1_status", "unknown"),
            module_a_status=result.get("module_a_status", "unknown"),
            module_b_status=result.get("module_b_status", "unknown"),
            agent1_error=result.get("agent1_error"),
            module_a_error=result.get("module_a_error"),
            module_b_error=result.get("module_b_error"),
        ),
        data={
            "query": result.get("query"),
            "location": result.get("location"),
            "jobs": result.get("jobs", []),
            "tips": result.get("tips", ""),
            "questions": result.get("questions", []),
        },
    )


@app.post("/api/v1/master-graph", response_model=MasterGraphResponse)
async def master_graph(request: MasterGraphRequest):
    return _run_master_graph(request)




@app.get("/health")
async def health():
    return {
        "status": "ok",
        "module": "Module D",
        "master_graph": "/api/v1/master-graph",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8082)
