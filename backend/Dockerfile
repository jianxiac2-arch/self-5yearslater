FROM python:3.12-slim

WORKDIR /app

# 国内镜像加速
ENV HF_ENDPOINT=https://hf-mirror.com \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PYTHONUNBUFFERED=1

# 本地 Docker 一键启动用 BGE 本地 embedding，装完整依赖（含 sentence-transformers）。
# 生产部署（Railway/Nixpacks）只读 requirements.txt，走 DeepSeek Embedding API，免 torch。
COPY requirements.txt requirements-local.txt ./
RUN pip install --no-cache-dir -r requirements-local.txt

COPY app ./app

EXPOSE 8000

# 启动时先写入认知框架（幂等），再起服务
CMD ["sh", "-c", "python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
