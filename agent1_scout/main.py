import os
import sys
import time
import json
import asyncio
import logging
from copy import deepcopy
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SerpAPIWrapper
from langchain_core.prompts import ChatPromptTemplate
from cachetools import TTLCache

# [ZH] 修复 Windows cmd 打印非 ASCII 字符导致 GBK 编码崩溃
# [EN] Fix GBK encoding crash when printing non-ASCII chars in Windows cmd
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# [ZH] 加载 .env 文件中的环境变量（支持直接 python main.py 启动）
# [EN] Load environment variables from .env file (supports direct python main.py startup)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


# [ZH] 配置日志格式（替代 print，带时间戳和级别）
# [EN] Configure structured logging (replaces print, adds timestamp and level)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("agent1")


# ==========================================
# 1. 定义数据结构 (A2A 通信协议)
# 1. Define Data Structures (A2A Communication Protocol)
# ==========================================

class ScoutRequest(BaseModel):
    location: str = Field(default="Greater Boston Area", description="搜索的地理位置 / Geographic location for the search")
    keywords: str = Field(default="Data Scientist AI Intern Wayfair Hubspot", description="搜索关键词 / Search keywords")
    # 【优化点 1：参数校验防御 / Optimization 1: Input Validation & Defense】
    num_results: int = Field(default=3, ge=1, le=10, description="希望返回的岗位数量(1-10) / Desired number of jobs (1-10)")

class JobJD(BaseModel):
    company: str = Field(description="公司名称 / Company name")
    job_title: str = Field(description="岗位名称 / Job title")
    estimated_salary: str = Field(description="预计薪资 (如 $40/hr, $80k-$100k, 或 'Not Specified') / Estimated salary or 'Not Specified'")
    core_skills: List[str] = Field(description="核心技能要求 (如 Python, SQL) / Core skill requirements (e.g., Python, SQL)")
    summary: str = Field(description="一句话总结职责 / A one-sentence summary of responsibilities")
    apply_link: str = Field(description="申请链接或来源 / Application link or original source")

class ScoutResponse(BaseModel):
    status: str = Field(description="任务执行状态 / Task execution status (e.g., success)")
    jobs: List[JobJD] = Field(description="提取出的结构化岗位列表 / Extracted structured list of jobs")


# ==========================================
# 2. 模块级常量 (LLM / Prompt / Cache)
# 2. Module-Level Constants (LLM / Prompt / Cache)
# ==========================================

# [ZH] LLM 和 Prompt 是无状态的，在模块加载时初始化一次即可，避免每次请求重复创建
# [EN] LLM and Prompt are stateless; initialize once at module load to avoid per-request overhead
PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a lightning-fast AI Job Scout. Extract internship info from the raw data. "
     "RULES:\n"
     "1. If 'company' is missing from the title, deduce it from the domain name in the Link.\n"
     "2. If 'core_skills' are missing, smartly infer 2-3 standard skills based on the job_title.\n"
     "3. For 'apply_link', ALWAYS strictly use the URL provided in the 'Link' field.\n"
     "4. Extract 'estimated_salary' if it appears in the snippet (e.g., '$40/hr'). If absent, output 'Not Specified'.\n"
     "5. CRITICAL: Output ONLY valid raw JSON. DO NOT wrap the output in ```json or any markdown blocks. JUST THE RAW JSON OBJECT."
    ),
    ("human", "Extract exactly {num} jobs from this raw data:\n\n{raw_data}")
])

# [ZH] 缓存：10 分钟 TTL，最多 50 条。重复搜索秒回，不浪费 API 配额
# [EN] Cache: 10-min TTL, max 50 items. Repeated searches return instantly, saving API quota
job_cache = TTLCache(maxsize=50, ttl=600)

# [ZH] LLM 和搜索工具：延迟初始化，首次调用时创建，之后复用
# [EN] LLM and search tool: lazy init on first call, then reused
_llm = None
_search_tool = None

def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0.0)
    return _llm

def get_search_tool():
    global _search_tool
    if _search_tool is None:
        _search_tool = SerpAPIWrapper()
    return _search_tool


# ==========================================
# 3. 核心 Agent 逻辑 (全异步 + 极速出图)
# 3. Core Agent Logic (Fully Asynchronous + Lightning Fast)
# ==========================================

async def run_scout_agent(request: ScoutRequest) -> ScoutResponse:

    if not os.getenv("GOOGLE_API_KEY") or not os.getenv("SERPAPI_API_KEY"):
        raise ValueError("[ZH] 缺少 API 密钥环境变量 / [EN] Missing API Key environment variables")

    search_query = f"{request.keywords} jobs in {request.location}"
    logger.info(f"Executing async search: {search_query}")

    try:
        raw_dict = await get_search_tool().aresults(search_query)

        formatted_results = []
        organic_results = raw_dict.get("organic_results", [])

        # [ZH] 只多拿 2 条备选，减轻大模型阅读负担 / [EN] Fetch 2 extra to reduce LLM input noise
        for res in organic_results[:request.num_results + 2]:
            title = res.get("title", "No Title")
            snippet = res.get("snippet", "No Snippet")
            link = res.get("link", "Not Available")
            formatted_results.append(f"Title: {title}\nSnippet: {snippet}\nLink: {link}")

        raw_search_results = "\n\n---\n\n".join(formatted_results)

    except Exception as e:
        raise Exception(f"SerpAPI call failed: {str(e)}")

    # [ZH] 搜索结果为空时直接返回，不要喂空数据给 LLM 产生幻觉
    # [EN] If no search results, return early instead of feeding empty data to LLM
    if not formatted_results:
        logger.warning("SerpAPI returned 0 organic results, returning empty response.")
        return ScoutResponse(status="success", jobs=[])

    # [ZH] 使用延迟初始化的 LLM 单例，避免重复创建
    # [EN] Use lazy-initialized LLM singleton to avoid re-creation per request
    structured_llm = get_llm().with_structured_output(ScoutResponse)
    chain = PROMPT | structured_llm

    logger.info("Using Gemini 3 to structure data...")

    # [ZH] 最多只容忍 1 次重试，第二次用 try/except 兜底
    # [EN] Tolerate at most 1 retry, with proper exception handling on the fallback
    try:
        result = await chain.ainvoke({
            "num": request.num_results,
            "raw_data": raw_search_results
        })
        return result
    except Exception as e:
        logger.warning(f"First attempt failed, trying one last fallback... Error: {e}")
        await asyncio.sleep(0.5)
        try:
            return await chain.ainvoke({
                "num": request.num_results,
                "raw_data": raw_search_results
            })
        except Exception as e2:
            raise Exception(f"LLM failed after 2 attempts. Last error: {e2}")


# ==========================================
# 4. 部署外壳 (FastAPI 封装)
# 4. Deployment Shell (FastAPI Wrapper)
# ==========================================

app = FastAPI(
    title="Job Scout Agent API",
    description="MIT NANDA Sandbox Project - Group 1. Lightning Fast Edition with Caching & Telemetry.",
    version="2.3.0"
)

# ==========================================
# NANDA Agent Card (/.well-known/agent.json)
# ==========================================

AGENT_CARD_PATH = Path(__file__).with_name("agent.json")
if AGENT_CARD_PATH.exists():
    with AGENT_CARD_PATH.open("r", encoding="utf-8") as _acf:
        AGENT_CARD_TEMPLATE = json.load(_acf)

    def get_agent_card() -> dict:
        """[ZH] 获取 NANDA Agent 事实卡 / [EN] Get NANDA Agent Fact Card."""
        card = deepcopy(AGENT_CARD_TEMPLATE)
        card["url"] = os.getenv("PUBLIC_URL", card.get("url", ""))
        return card

    @app.get("/.well-known/agent.json", tags=["NANDA"])
    async def agent_card():
        """[ZH] NANDA Agent 事实卡 / [EN] Machine-readable metadata for agent discovery."""
        return get_agent_card()


@app.get("/health", tags=["Ops"])
async def health():
    """[ZH] 健康检查端点 / [EN] Health check endpoint for monitoring."""
    return {"status": "ok", "agent": "job-scout", "version": "2.3.0"}

@app.post("/api/v1/scout", response_model=ScoutResponse, tags=["Scout Agent"])
async def api_scout_jobs(request: ScoutRequest):
    start_time = time.time()

    # [ZH] 构造缓存 Key（用 | 分隔避免冲突）/ [EN] Build cache key (use | separator to avoid collisions)
    cache_key = f"{request.location}|{request.keywords}|{request.num_results}"

    try:
        # [ZH] 命中缓存则秒回 / [EN] Cache hit = instant return
        if cache_key in job_cache:
            elapsed = time.time() - start_time
            logger.info(f"[CACHE HIT] Returned cached data in {elapsed:.3f}s")
            return job_cache[cache_key]

        response = await run_scout_agent(request)

        # [ZH] 存入缓存 / [EN] Store in cache
        job_cache[cache_key] = response

        elapsed = time.time() - start_time
        logger.info(f"[TASK COMPLETE] Search + LLM inference done in {elapsed:.2f}s")
        return response

    except ValueError as e:
        # [ZH] API Key 缺失等配置错误 / [EN] Config errors like missing API keys
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[TASK FAILED] Error after {elapsed:.2f}s: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)