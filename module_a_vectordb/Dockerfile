# ============================================
# Module A — Vector DB (Resume Tips)
# ============================================
FROM python:3.11-slim

WORKDIR /app

# [ZH] 安装编译依赖 / [EN] Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# [ZH] 安装 Python 依赖 / [EN] Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# [ZH] 复制应用代码 / [EN] Copy application code
COPY . .

# [ZH] 构建镜像时预建向量数据库 / [EN] Pre-build vector database during image build
RUN python build_db.py

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
