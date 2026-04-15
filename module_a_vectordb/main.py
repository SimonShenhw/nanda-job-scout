from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)

# 1. 启动 FastAPI
app = FastAPI(title="Module A: Vector DB API - Resume Tips")

# 2. 连接刚才生成的本地数据库
embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma(persist_directory="./chroma_data", embedding_function=embedding_function)


# 3. 定义接收的数据格式
class SearchQuery(BaseModel):
    query: str
    top_k: Optional[int] = 2


# 4. 健康检查接口
@app.get("/health")
async def health():
    return {"status": "ok"}


# 5. 开放对外的接口网址
@app.post("/api/v1/search")
async def search_vector_db(request: SearchQuery):
    docs = db.similarity_search(request.query, k=request.top_k)
    result = "\n\n".join([doc.page_content for doc in docs])
    return {"status": "success", "result": result}
