"""Pydantic 模型：API 请求/响应的数据结构。

对应 spec 第 4 节的各层记忆，以及对话/搜索/总结的接口契约。
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ===== 记忆库各层 =====

class ProfileItem(BaseModel):
    """L1 用户画像。"""
    key: str
    value: str
    confidence: Optional[float] = None
    source: str = "manual"


class Fact(BaseModel):
    """L2 关键事实。"""
    id: str
    category: str
    content: str
    importance: float = 0.5
    source: str = "manual"


class Preference(BaseModel):
    """L3 偏好。"""
    id: str
    type: str  # like | dislike | style | taboo
    content: str
    importance: float = 0.5


class Episode(BaseModel):
    """L4 事件。"""
    id: str
    conversation_id: Optional[str] = None
    summary: str
    importance: float = 0.5
    topics: list[str] = []
    entities: list[str] = []
    occurred_at: Optional[datetime] = None


class Reflection(BaseModel):
    """L5 反思。"""
    id: str
    type: str  # pattern | trend | blindspot | change
    content: str
    evidence: list[str] = []


class Framework(BaseModel):
    """L6 认知框架。"""
    id: str
    type: str  # thinking_tool | population_profile | decision_framework
    name: str
    content: str
    trigger_conditions: str = ""


# ===== 对话 =====

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    """对话请求。"""
    conversation_id: Optional[str] = None
    message: str


class ChatStreamChunk(BaseModel):
    """流式回复的单个片段。"""
    delta: str = ""
    done: bool = False
    conversation_id: Optional[str] = None
    meta: Optional[dict] = None  # 调用了哪些框架、检索了哪些记忆等


# ===== 元认知 =====

class SearchRequest(BaseModel):
    """搜索记忆。"""
    query: str
    layers: list[str] = Field(default=[], description="限定层，如 ['facts','episodes']")
    limit: int = 10


class SearchHit(BaseModel):
    layer: str
    id: str
    content: str
    score: Optional[float] = None
    extra: Optional[dict] = None


class SearchResponse(BaseModel):
    hits: list[SearchHit]


class SummaryRequest(BaseModel):
    """总结记忆。"""
    dimension: str  # time | topic | person
    value: str  # 如 "过去一个月" / "职业选择" / "某人物"
    save_as_reflection: bool = False


class SummaryResponse(BaseModel):
    summary: str
    reflection_id: Optional[str] = None
