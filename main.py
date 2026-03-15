import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
# 【修改点 1】：引入 Google GenAI 的库，而不是 OpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SerpAPIWrapper
from langchain_core.prompts import ChatPromptTemplate

# ==========================================
# 1. 定义数据结构 (这是 A2A 通信的灵魂，确保输出标准 JSON)
# ==========================================

class ScoutRequest(BaseModel):
    location: str = Field(default="Greater Boston Area", description="搜索的地理位置")
    keywords: str = Field(default="Data Scientist AI Intern Wayfair Hubspot", description="搜索关键词")
    num_results: int = Field(default=3, description="希望返回的岗位数量")

class JobJD(BaseModel):
    company: str = Field(description="公司名称")
    job_title: str = Field(description="岗位名称")
    core_skills: List[str] = Field(description="核心技能要求 (如 Python, SQL, PyTorch)")
    summary: str = Field(description="一句话总结这个岗位的职责")
    apply_link: str = Field(description="原始来源或申请链接 (如果有的话)")

class ScoutResponse(BaseModel):
    status: str = Field(description="任务执行状态 (如 success)")
    jobs: List[JobJD] = Field(description="提取出的结构化岗位列表")


# ==========================================
# 2. 核心 Agent 逻辑 (LangChain + SerpAPI 工具)
# ==========================================

def run_scout_agent(request: ScoutRequest) -> ScoutResponse:
    # 【修改点 2】：检查 GOOGLE_API_KEY 而不是 OPENAI
    if not os.getenv("GOOGLE_API_KEY") or not os.getenv("SERPAPI_API_KEY"):
        raise ValueError("缺少 GOOGLE_API_KEY 或 SERPAPI_API_KEY 环境变量！请在 Replit 的 Secrets 中配置。")

    # 1. 初始化工具：SerpAPI
    search_tool = SerpAPIWrapper()
    search_query = f"{request.keywords} jobs in {request.location}"
    print(f"Agent 正在执行搜索任务: {search_query}...")

    raw_search_results = search_tool.run(search_query)

    # 【修改点 3】：使用 Gemini 1.5 Flash 大模型 (速度快，完全胜任信息提取)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
    structured_llm = llm.with_structured_output(ScoutResponse)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的 AI 猎头助手(Job Scout Agent)。你的任务是从杂乱的搜索结果中，提取出实习岗位的结构化信息。如果某些信息缺失，请填入 'Not Available'。"),
        ("human", "请从以下外部工具(SerpAPI)抓取回来的原始内容中，提取出最多 {num} 个岗位的信息。\n\n原始内容:\n{raw_data}")
    ])

    chain = prompt | structured_llm

    print("Agent 正在利用 Gemini 清洗并提取结构化数据...")
    result = chain.invoke({
        "num": request.num_results,
        "raw_data": raw_search_results
    })

    return result

# ==========================================
# 3. 部署外壳 (FastAPI 封装，供 NANDA Sandbox 调用)
# ==========================================

app = FastAPI(
    title="岗位侦察兵 API (Job Scout Agent)",
    description="MIT NANDA Sandbox Project - Group X. 用于抓取并结构化提取波士顿地区 AI/DS 实习岗位的 Agent。",
    version="1.0.0"
)

@app.post("/api/v1/scout", response_model=ScoutResponse, tags=["Scout Agent"])
async def api_scout_jobs(request: ScoutRequest):
    try:
        response = run_scout_agent(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # 必须是 0.0.0.0 和 8080，Replit 才能把你的接口暴露给外网
    uvicorn.run(app, host="0.0.0.0", port=8080)
