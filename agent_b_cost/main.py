"""
main.py — Agent B 的 FastAPI 服务入口
main.py — FastAPI service entry point for Agent B

把 Agent B 的核心逻辑包装成 HTTP 接口，运行在端口 8083。
Wraps Agent B's core logic into HTTP endpoints, running on port 8083.

接口列表 / Endpoints:
  POST /api/v1/evaluate  — 核心评估接口，供 Agent A 调用 / Main endpoint for Agent A
  GET  /api/v1/cities    — 返回支持的城市列表 / Returns supported cities
  GET  /health           — 健康检查 / Health check
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from agent import evaluate_job
from tools import CITY_COST_DATA


# ============================================================
# 初始化 FastAPI 应用
# Initialize FastAPI app
# ============================================================

app = FastAPI(
    title="Life Cost Calculator — Agent B",
    description=(
        "NANDA Society of Agents — Agent B. "
        "Evaluates cost of living and salary affordability for any city. "
        "Called by Agent A (Job Scout) to enrich job listings."
    ),
    version="1.0.0",
)


# ============================================================
# 数据格式定义（请求 & 响应）
# Data Models (Request & Response)
# ============================================================

class EvaluateRequest(BaseModel):
    """
    Agent A 发给 Agent B 的请求格式
    Request format sent from Agent A to Agent B
    """
    job_title: str = Field(
        description="Job title, e.g. 'Data Scientist'",
        example="Data Scientist"
    )
    location: str = Field(
        description="City name, e.g. 'Boston, MA' or 'Greater Boston Area'",
        example="Boston, MA"
    )
    estimated_salary: str = Field(
        default="Not Specified",
        description="Salary string from Agent A, e.g. '$80k - $100k' or '$30 - $35/hr'",
        example="$80k - $100k"
    )


class AgentAPayload(BaseModel):
    """
    返回给 Agent A 的精简字段
    Short fields returned to Agent A
    """
    monthly_cost_range: str
    affordability: str


class CostBreakdown(BaseModel):
    """
    费用明细
    Cost breakdown details
    """
    rent: str
    food: str
    commute: str
    necessities: str


class Notes(BaseModel):
    """
    补充说明（薪资兜底提示、城市兜底提示）
    Extra notes (salary fallback notice, city fallback notice)
    """
    salary_note: Optional[str] = None
    city_note:   Optional[str] = None


class EvaluateResponse(BaseModel):
    """
    Agent B 完整的返回结果格式
    Full response format from Agent B
    """
    status:                str
    job_title:             str
    city:                  str
    monthly_salary_range:  str
    monthly_cost_range:    str
    monthly_surplus_range: str
    affordability:         str
    ai_comment:            str
    cost_breakdown:        CostBreakdown
    notes:                 Notes
    for_agent_a:           AgentAPayload


# ============================================================
# 接口 1：核心评估接口（Agent A 调用这个）
# Endpoint 1: Main evaluate endpoint (Agent A calls this)
# ============================================================

@app.post(
    "/api/v1/evaluate",
    response_model=EvaluateResponse,
    tags=["Life Cost Calculator"],
    summary="Evaluate cost of living and salary affordability for a job"
)
async def evaluate(request: EvaluateRequest):
    """
    接收职位信息，返回生活成本评估结果。
    Receives job info and returns a full cost of living evaluation.

    Agent A 只需要使用 for_agent_a 字段里的两个值：
    Agent A only needs the two values inside the for_agent_a field:
      - monthly_cost_range : 月生活成本范围 / Monthly living cost range
      - affordability      : 财务状态评级 / Financial status rating
    """
    try:
        result = await evaluate_job(
            job_title=request.job_title,
            location=request.location,
            estimated_salary=request.estimated_salary,
        )
        return EvaluateResponse(
            status="success",
            job_title=result["job_title"],
            city=result["city"],
            monthly_salary_range=result["monthly_salary_range"],
            monthly_cost_range=result["monthly_cost_range"],
            monthly_surplus_range=result["monthly_surplus_range"],
            affordability=result["affordability"],
            ai_comment=result["ai_comment"],
            cost_breakdown=CostBreakdown(**result["cost_breakdown"]),
            notes=Notes(**result["notes"]),
            for_agent_a=AgentAPayload(**result["for_agent_a"]),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 接口 2：返回支持的城市列表
# Endpoint 2: Return list of supported cities
# ============================================================

@app.get(
    "/api/v1/cities",
    tags=["Life Cost Calculator"],
    summary="Get the list of supported cities"
)
async def get_cities():
    """
    返回 Agent B 内置数据支持的城市列表。
    Returns the list of cities supported by Agent B's built-in data.
    """
    return {
        "status": "success",
        "supported_cities": list(CITY_COST_DATA.keys()),
        "note": "Other cities will fall back to the nearest supported city."
    }


# ============================================================
# 接口 3：健康检查
# Endpoint 3: Health check
# ============================================================

@app.get(
    "/health",
    tags=["Ops"],
    summary="Health check"
)
async def health():
    """
    健康检查接口，供 Module D 编排器检测服务状态。
    Health check endpoint for Module D orchestrator to monitor this service.
    """
    return {
        "status": "ok",
        "agent": "life-cost-calculator",
        "version": "1.0.0",
        "port": 8083
    }


# ============================================================
# 启动服务
# Start the service
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)