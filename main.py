import os
import asyncio  # [ZH] 引入 Python 原生的异步等待库 / [EN] Import Python's native async library
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SerpAPIWrapper
from langchain_core.prompts import ChatPromptTemplate

# ==========================================
# 1. 定义数据结构 (A2A 通信协议)
# 1. Define Data Structures (A2A Communication Protocol)
# ==========================================

class ScoutRequest(BaseModel):
    location: str = Field(default="Greater Boston Area", description="搜索的地理位置 / Geographic location for the search")
    keywords: str = Field(default="Data Scientist AI Intern Wayfair Hubspot", description="搜索关键词 / Search keywords")
    
    # 【🔥 优化点 1：参数校验防御 / Optimization 1: Input Validation & Defense】
    # [ZH] 限制外部调用最多要 10 条结果 (le=10)，最少 1 条 (ge=1)，防恶意刷量。
    # [EN] Restrict external calls to a max of 10 results (le=10) and min of 1 (ge=1) to prevent API quota exhaustion.
    num_results: int = Field(default=3, ge=1, le=10, description="希望返回的岗位数量(1-10) / Desired number of jobs (1-10)")

class JobJD(BaseModel):
    company: str = Field(description="公司名称 / Company name")
    job_title: str = Field(description="岗位名称 / Job title")
    core_skills: List[str] = Field(description="核心技能要求 (如 Python, SQL) / Core skill requirements (e.g., Python, SQL)")
    summary: str = Field(description="一句话总结职责 / A one-sentence summary of responsibilities")
    apply_link: str = Field(description="申请链接或来源 / Application link or original source")

class ScoutResponse(BaseModel):
    status: str = Field(description="任务执行状态 / Task execution status (e.g., success)")
    jobs: List[JobJD] = Field(description="提取出的结构化岗位列表 / Extracted structured list of jobs")


# ==========================================
# 2. 核心 Agent 逻辑 (全异步 + 容错机制)
# 2. Core Agent Logic (Fully Asynchronous + Fault Tolerance)
# ==========================================

# 【🔥 优化点 2：真正的异步协程 / Optimization 2: True Asynchronous Coroutines】
# [ZH] 使用 async def 防止阻塞 FastAPI 服务器，极大提升高并发性能。
# [EN] Using async def prevents blocking the FastAPI server, greatly improving high-concurrency performance.
async def run_scout_agent(request: ScoutRequest) -> ScoutResponse:
    
    if not os.getenv("GOOGLE_API_KEY") or not os.getenv("SERPAPI_API_KEY"):
        raise ValueError("[ZH] 缺少 API 密钥环境变量 / [EN] Missing API Key environment variables")

    # [ZH] 1. 初始化外部搜索工具 /[EN] 1. Initialize external search tool
    search_tool = SerpAPIWrapper()
    search_query = f"{request.keywords} jobs in {request.location}"
    print(f"Agent is executing async search task: {search_query}...")

    try:
        # [ZH] 使用异步 .arun() / [EN] Use asynchronous .arun()
        raw_search_results = await search_tool.arun(search_query)
    except Exception as e:
        raise Exception(f"[ZH] SerpAPI 调用失败 / [EN] SerpAPI call failed: {str(e)}")

    # [ZH] 2. 初始化大模型大脑 (2.5版本) / [EN] 2. Initialize LLM Brain (v2.5)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
    structured_llm = llm.with_structured_output(ScoutResponse)

    # [ZH] 3. 构造英文 Prompt (提升输出稳定性) /[EN] 3. Construct English Prompt (improves output stability)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a professional AI Job Scout Agent. Your task is to extract structured internship job information from messy search results. If any info is missing, fill in 'Not Available'."),
        ("human", "Please extract information for up to {num} jobs from the following raw content scraped by SerpAPI.\n\nRaw Content:\n{raw_data}")
    ])

    chain = prompt | structured_llm

    print("Agent is using Gemini to clean and structure data...")

    # 【🔥 优化点 3：LLM 容错与自动重试 / Optimization 3: LLM Retry Logic】
    # [ZH] 大模型偶发解析失败时，最多自动重试 3 次。
    # [EN] Auto-retry up to 3 times if the LLM occasionally fails to parse the data.
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # [ZH] 使用异步 .ainvoke() / [EN] Use asynchronous .ainvoke()
            result = await chain.ainvoke({
                "num": request.num_results,
                "raw_data": raw_search_results
            })
            return result
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed, retrying... Error: {e}")
            if attempt == max_retries - 1:
                # [ZH] 3次都失败才抛出错误 / [EN] Raise error only if all 3 attempts fail
                raise Exception("[ZH] 大模型解析失败 / [EN] LLM failed to parse data.")
            await asyncio.sleep(1) # [ZH] 休息1秒 / [EN] Wait 1 second before retry


# ==========================================
# 3. 部署外壳 (FastAPI 封装)
# 3. Deployment Shell (FastAPI Wrapper)
# ==========================================

app = FastAPI(
    title="Job Scout Agent API",
    description="MIT NANDA Sandbox Project - Group X. Industry-grade Agent API supporting A2A communication, high concurrency, and fault tolerance.",
    version="2.0.0"
)

@app.post("/api/v1/scout", response_model=ScoutResponse, tags=["Scout Agent"])
async def api_scout_jobs(request: ScoutRequest):
    try:
        # [ZH] 等待异步任务完成 / [EN] Await the asynchronous task
        response = await run_scout_agent(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # [ZH] 必须绑定 0.0.0.0 才能对外网提供服务 / [EN] Must bind to 0.0.0.0 to expose API to the public internet
    uvicorn.run(app, host="0.0.0.0", port=8080)
