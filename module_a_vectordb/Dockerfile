# 1. 选择基础镜像 (也就是你的 "操作系统+Python发动机")
# 我们选用 3.11 的精简版，体积小且匹配你的本地环境
FROM python:3.11-slim

# 2. 设置工作目录 (相当于在集装箱里建了一个叫 /app 的文件夹)
WORKDIR /app

# 3. 先把清单库复制进去 (这一步单独拿出来是为了利用缓存，加快后续打包速度)
COPY requirements.txt .

# 4. 安装所有的依赖包 (LangChain, FastAPI, ChromaDB 等)
# --no-cache-dir 是为了让打包出来的体积更小
RUN pip install --no-cache-dir -r requirements.txt

# 5. 把你本地的所有代码和数据 (main.py, build_db.py, chroma_data等) 拷贝到集装箱里
COPY . .

# 6. 暴露 8000 端口 (告诉集装箱，我们要在这个窗口对外营业)
EXPOSE 8000

# 7. 启动指令 (集装箱落地后，自动执行这句命令启动你的微服务)
# 注意：在 Docker 里必须用 0.0.0.0 而不是 127.0.0.1，这样外部才能访问
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]