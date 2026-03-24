from fastapi import FastAPI
from pydantic import BaseModel
from langchain.tools import tool
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)

# 1. 启动 FastAPI
app = FastAPI(title="Module A: Vector DB API - Resume Tips")

# 2. 连接刚才生成的本地数据库
embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma(persist_directory="./chroma_data", embedding_function=embedding_function)


# 3. 包装为 LangChain @tool，方便 Agent 2 (Code B) 调用
@tool
def retrieve_resume_tips(query: str) -> str:
    """Useful for retrieving tech resume tips and interview strategies."""
    docs = db.similarity_search(query, k=2)
    return "\n\n".join([doc.page_content for doc in docs])


# 4. 定义接收的数据格式
class SearchQuery(BaseModel):
    query: str


# 5. 开放对外的接口网址
@app.post("/api/v1/search")
async def search_vector_db(request: SearchQuery):
    # 调用工具搜索数据库
    result = retrieve_resume_tips.invoke({"query": request.query})
    return {"status": "success", "result": result}
