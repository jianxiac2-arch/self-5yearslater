"""ChromaDB 向量库：记忆库的语义检索层。

L2/L4/L5/L6 中需要语义检索的内容都存这里，与 SQLite 通过 vector_id 关联。
embedding 支持两种模式：
- 开发环境：本地 BGE-small-zh（首次启动自动下载，约 100MB）
- 生产环境：HuggingFace Inference API（设 EMBEDDING_API_URL 即可，免本地模型）
"""
import logging
import requests as _requests
import chromadb
from app.config import settings

logger = logging.getLogger(__name__)

_client: chromadb.api.ClientAPI | None = None
_ef = None

COLLECTION_FACTS = "facts"
COLLECTION_EPISODES = "episodes"
COLLECTION_REFLECTIONS = "reflections"
COLLECTION_FRAMEWORKS = "frameworks"


class _APIEmbeddingFunction:
    """通过 API 做 embedding（支持 DeepSeek / HuggingFace Inference）。"""

    def __init__(self, api_url: str, api_key: str = "", model: str = ""):
        self._api_url = api_url
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        self._model = model

    def _call(self, texts: list[str]) -> list[list[float]]:
        payload = {"input": texts}
        if self._model:
            payload["model"] = self._model
        resp = _requests.post(
            self._api_url,
            headers=self._headers,
            json=payload,
            timeout=30,
        )
        if resp.status_code >= 400:
            # 打印响应体，避免 raise_for_status 吞掉服务端的错误详情
            logger.error(
                "Embedding API failed: HTTP %s, model=%s, url=%s, response=%s",
                resp.status_code, self._model, self._api_url, resp.text[:300],
            )
        resp.raise_for_status()
        data = resp.json()

        # DeepSeek 格式: {"data": [{"embedding": [...]}]}
        if isinstance(data, dict) and "data" in data:
            return [item["embedding"] for item in data["data"]]
        # HuggingFace 格式: [[float, ...], ...]
        if isinstance(data, list) and isinstance(data[0], list):
            return data
        raise RuntimeError(f"Unexpected embedding response: {str(data)[:200]}")

    def __call__(self, input):
        return self._call(input if isinstance(input, list) else [input])

    def embed_query(self, input):
        return self._call([input])[0]

    def embed_documents(self, input):
        return self._call(input)

    def name(self):
        return "api_embedding"


class _BGEEmbeddingFunction:
    """本地 SentenceTransformer 包装。"""

    def __init__(self, model):
        self._model = model

    def __call__(self, input):
        return self._model.encode(input).tolist()

    def embed_query(self, input):
        return self._model.encode(input).tolist()

    def embed_documents(self, input):
        return self._model.encode(input).tolist()

    def name(self):
        return "sentence_transformer"


def get_embedding_function():
    """懒加载 embedding，优先用 API（生产），回退本地（开发）。"""
    global _ef
    if _ef is None:
        if settings.embedding_api_url:
            logger.info("Using API for embedding: %s (model: %s)", settings.embedding_api_url, settings.embedding_api_model)
            _ef = _APIEmbeddingFunction(
                settings.embedding_api_url,
                settings.embedding_api_key,
                settings.embedding_api_model,
            )
        else:
            logger.info("Loading local embedding model: %s", settings.embedding_model)
            from sentence_transformers import SentenceTransformer
            _ef = _BGEEmbeddingFunction(SentenceTransformer(settings.embedding_model))
    return _ef


def get_client() -> chromadb.api.ClientAPI:
    """懒加载 ChromaDB 持久化客户端。"""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_path)
    return _client


def get_collection(name: str) -> chromadb.api.Collection:
    return get_client().get_or_create_collection(
        name=name,
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def init_vector_store() -> None:
    """初始化所有 collection。幂等。"""
    for name in [
        COLLECTION_FACTS,
        COLLECTION_EPISODES,
        COLLECTION_REFLECTIONS,
        COLLECTION_FRAMEWORKS,
    ]:
        get_collection(name)
        logger.info("Collection ready: %s", name)
