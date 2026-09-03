"""全局配置：通过 .env 文件 + 环境变量读取。

所有路径、API Key、模型名称都集中在这里，方便修改。
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录
BASE_DIR = Path(__file__).resolve().parent.parent
# 数据目录：SQLite + ChromaDB 都放在这里，便于备份和迁移
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "memory.db"
CHROMA_PATH = DATA_DIR / "chroma"


class Settings(BaseSettings):
    # --- LLM (DeepSeek, OpenAI 兼容) ---
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    chat_model: str = "deepseek-chat"

    # --- Embedding ---
    # 生产环境：用 DeepSeek Embedding API（免本地模型，同 API Key）
    # 开发环境：不设则用本地 BGE-small-zh（首次启动自动下载）
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_api_url: str = ""  # 设为 https://api.deepseek.com/v1/embeddings 即用 API
    embedding_api_key: str = ""  # DeepSeek API Key（同 LLM key）
    embedding_api_model: str = "text-embedding-v1"  # DeepSeek embedding 模型名

    # --- 路径 ---
    db_path: str = str(DB_PATH)
    chroma_path: str = str(CHROMA_PATH)

    # --- 服务 ---
    port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    # --- 公网部署 ---
    # 访问口令：设为非空后，所有 /api 请求（除 /api/auth/status）需带 X-Access-Code 头。
    # 本地开发留空即不启用。
    access_code: str = ""
    # 演示数据：设为 true 时，启动种子脚本会写入半虚拟演示人格（公网 demo 用）。
    seed_demo_data: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# 启动时确保数据目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
