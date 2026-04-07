# Agent 1 — Job Scout

[English](#english) | [中文](#中文)

---

## English

AI-powered job search agent that discovers real-time job listings and structures them into clean, actionable data. Built as a standalone microservice in the NANDA Agent-to-Agent (A2A) ecosystem.

### How It Works

```
User Request (keywords + location)
    │
    ▼
SerpAPI — Real-time Google Jobs search
    │
    ▼
Gemini LLM — Structured extraction (job title, company, salary, skills, link)
    │
    ▼
JSON Response — Clean, validated job data
```

### Features

- **Real-time Search** — SerpAPI integration for live Google Jobs results
- **LLM Structuring** — Gemini 3 Flash extracts and normalizes job data into a strict schema
- **Salary Extraction** — Automatically detects salary info from snippets ($40/hr, $80k-$100k), or returns "Not Specified"
- **Skill Inference** — If core skills are missing from the listing, the LLM infers 2-3 relevant skills from the job title
- **TTL Caching** — 10-minute cache (max 50 entries) for instant repeat searches, saving API quota
- **Async-first** — Fully asynchronous architecture with FastAPI + Uvicorn
- **Retry Logic** — 1 automatic retry on LLM failure with graceful error handling
- **Input Validation** — Pydantic models enforce constraints (num_results: 1-10)
- **A2A Compatible** — JSON output aligns with Agent 2's input schema for seamless inter-agent communication

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/scout` | Search and structure job listings |
| GET | `/health` | Health check |

### Request / Response

**POST `/api/v1/scout`**

Request:
```json
{
  "location": "Greater Boston Area",
  "keywords": "Data Scientist AI Intern",
  "num_results": 3
}
```

Response:
```json
{
  "status": "success",
  "jobs": [
    {
      "company": "HubSpot",
      "job_title": "AI Research Intern",
      "estimated_salary": "$40/hr",
      "core_skills": ["Python", "NLP", "TensorFlow"],
      "summary": "Develop NLP features for marketing automation platform",
      "apply_link": "https://hubspot.com/careers/..."
    }
  ]
}
```

### Quick Start

#### Prerequisites

- Python 3.11+
- API keys: `GOOGLE_API_KEY` (Gemini) and `SERPAPI_API_KEY`

#### Run Locally

1. Create a `.env` file:
   ```
   GOOGLE_API_KEY=your_google_api_key
   SERPAPI_API_KEY=your_serpapi_key
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Windows + Python 3.14 only) Fix aiohttp DNS issue:
   ```bash
   pip uninstall aiodns -y
   ```

4. Start the server:
   ```bash
   python main.py
   ```

5. Test it:
   ```bash
   curl -X POST http://localhost:8080/api/v1/scout \
     -H "Content-Type: application/json" \
     -d '{"keywords": "AI Intern", "location": "Boston", "num_results": 2}'
   ```

#### Run with Docker

```bash
docker-compose up --build
```

### Tech Stack

- **LLM**: Google Gemini (gemini-3-flash-preview)
- **Search**: SerpAPI (Google Jobs)
- **Framework**: FastAPI + Uvicorn
- **Caching**: cachetools (TTLCache)
- **Validation**: Pydantic v2
- **Orchestration**: LangChain (ChatPromptTemplate + Structured Output)

### Project Structure

```
agent1_scout/
├── main.py              # FastAPI server + core agent logic
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container image definition
└── docker-compose.yml   # Standalone deployment config
```

### Architecture Context

In the full JobScout AI platform, Agent 1 is the first node in the LangGraph pipeline:

```
Module D (Orchestrator)
    │
    ├──► Agent 1 (this) ──► search + structure jobs
    ├──► Module A         ──► resume tips (runs in parallel)
    ├──► Agent 2          ──► interview questions (runs in parallel)
    └──► Agent B          ──► cost of living (runs in parallel)
```

Agent 1's output feeds directly into Agent 2 and Agent B for downstream processing.

---

## 中文

基于 AI 的岗位搜索 Agent，能够实时发现岗位并将其结构化为干净、可操作的数据。作为 NANDA Agent-to-Agent (A2A) 生态中的独立微服务构建。

### 工作原理

```
用户请求（关键词 + 地区）
    │
    ▼
SerpAPI — 实时 Google Jobs 搜索
    │
    ▼
Gemini LLM — 结构化提取（职位、公司、薪资、技能、链接）
    │
    ▼
JSON 响应 — 干净、经过验证的岗位数据
```

### 功能特性

- **实时搜索** — 集成 SerpAPI 获取实时 Google Jobs 结果
- **LLM 结构化** — Gemini 3 Flash 将原始数据提取并规范化为严格的 JSON 模式
- **薪资提取** — 自动从摘要中检测薪资信息（$40/hr、$80k-$100k），无信息时返回 "Not Specified"
- **技能推断** — 岗位信息中缺少核心技能时，LLM 根据职位名称推断 2-3 个相关技能
- **TTL 缓存** — 10 分钟缓存（最多 50 条），重复搜索秒回，节省 API 配额
- **异步优先** — 基于 FastAPI + Uvicorn 的全异步架构
- **重试机制** — LLM 失败时自动重试 1 次，配合优雅的错误处理
- **输入校验** — Pydantic 模型强制约束参数（num_results: 1-10）
- **A2A 兼容** — JSON 输出与 Agent 2 的输入模式对齐，实现无缝 Agent 间通信

### API 接口

| 方法 | 接口 | 说明 |
|------|------|------|
| POST | `/api/v1/scout` | 搜索并结构化岗位列表 |
| GET | `/health` | 健康检查 |

### 请求 / 响应格式

**POST `/api/v1/scout`**

请求：
```json
{
  "location": "Greater Boston Area",
  "keywords": "Data Scientist AI Intern",
  "num_results": 3
}
```

响应：
```json
{
  "status": "success",
  "jobs": [
    {
      "company": "HubSpot",
      "job_title": "AI Research Intern",
      "estimated_salary": "$40/hr",
      "core_skills": ["Python", "NLP", "TensorFlow"],
      "summary": "为营销自动化平台开发 NLP 功能",
      "apply_link": "https://hubspot.com/careers/..."
    }
  ]
}
```

### 快速开始

#### 前置要求

- Python 3.11+
- API 密钥：`GOOGLE_API_KEY`（Gemini）和 `SERPAPI_API_KEY`

#### 本地运行

1. 创建 `.env` 文件：
   ```
   GOOGLE_API_KEY=你的_google_api_key
   SERPAPI_API_KEY=你的_serpapi_key
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. （仅 Windows + Python 3.14）修复 aiohttp DNS 问题：
   ```bash
   pip uninstall aiodns -y
   ```

4. 启动服务：
   ```bash
   python main.py
   ```

5. 测试：
   ```bash
   curl -X POST http://localhost:8080/api/v1/scout \
     -H "Content-Type: application/json" \
     -d '{"keywords": "AI Intern", "location": "Boston", "num_results": 2}'
   ```

#### Docker 运行

```bash
docker-compose up --build
```

### 技术栈

- **大语言模型**：Google Gemini（gemini-3-flash-preview）
- **搜索引擎**：SerpAPI（Google Jobs）
- **后端框架**：FastAPI + Uvicorn
- **缓存**：cachetools（TTLCache）
- **数据验证**：Pydantic v2
- **编排**：LangChain（ChatPromptTemplate + Structured Output）

### 项目结构

```
agent1_scout/
├── main.py              # FastAPI 服务 + 核心 Agent 逻辑
├── requirements.txt     # Python 依赖
├── Dockerfile           # 容器镜像定义
└── docker-compose.yml   # 独立部署配置
```

### 架构上下文

在完整的 JobScout AI 平台中，Agent 1 是 LangGraph 流水线的第一个节点：

```
Module D（编排器）
    │
    ├──► Agent 1（本服务）──► 搜索 + 结构化岗位
    ├──► Module A          ──► 简历建议（并行执行）
    ├──► Agent 2           ──► 面试题生成（并行执行）
    └──► Agent B           ──► 生活成本评估（并行执行）
```

Agent 1 的输出直接馈入 Agent 2 和 Agent B 进行下游处理。
