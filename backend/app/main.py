"""FastAPI 入口。

启动时初始化 SQLite + ChromaDB，提供 /health 健康检查。
路由在后续任务中逐步挂载。
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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


@app.middleware("http")
async def access_code_gate(request: Request, call_next):
    """公网部署访问口令：设了 ACCESS_CODE 后，/api/* 需带 X-Access-Code 头。

    豁免：/health、/api/auth/status、CORS 预检（OPTIONS）。
    本地开发未设 ACCESS_CODE 时本中间件直接放行。
    """
    if settings.access_code and request.url.path.startswith("/api/"):
        if request.method != "OPTIONS" and request.url.path != "/api/auth/status":
            code = request.headers.get("x-access-code", "")
            if code != settings.access_code:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "访问口令无效或缺失（access code required）"},
                )
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok", "service": "5-years-later", "version": "0.1.0"}


@app.get("/api/auth/status")
def auth_status():
    """前端启动时探测：本实例是否开启访问口令。"""
    return {"auth_required": bool(settings.access_code)}


@app.post("/api/admin/reset-demo")
def reset_demo():
    """恢复演示数据（清空访客产生的内容，重建框架 + 演示人格）。"""
    if not settings.seed_demo_data:
        raise HTTPException(status_code=400, detail="本实例未启用演示数据")
    from app.seed import reset_demo_data
    reset_demo_data()
    return {"status": "ok", "detail": "演示数据已重置"}


app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(meta.router, prefix="/api/meta", tags=["meta"])
