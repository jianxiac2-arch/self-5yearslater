"""FastAPI 入口。

启动时初始化 SQLite + ChromaDB，提供 /health 健康检查。
路由在后续任务中逐步挂载。
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.vector_store import init_vector_store
from app.routers import chat, memory, meta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("5yl")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    logger.info("Initializing SQLite...")
    init_db()
    logger.info("Initializing ChromaDB (首次会下载 embedding 模型)...")
    try:
        init_vector_store()
    except Exception as e:
        logger.warning("向量库初始化失败（可继续，按需重试）: %s", e)
    logger.info("Startup done. Listening on port %s", settings.port)
    yield
    # 关闭（暂无资源需释放）
    logger.info("Shutdown.")


app = FastAPI(
    title="5 Years Later",
    description="个人 Agent：分层记忆库 + 认知框架层 + 反谄媚推理",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "5-years-later", "version": "0.1.0"}


app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(meta.router, prefix="/api/meta", tags=["meta"])
