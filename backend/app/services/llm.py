"""LLM 服务：调用 DeepSeek（OpenAI 兼容接口）。

提供非流式和流式两种调用方式。所有模型调用都走这里，方便统一管理。
"""
import logging
from typing import Iterator
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    """懒加载 OpenAI 客户端（指向 DeepSeek）。"""
    global _client
    if _client is None:
        if not settings.deepseek_api_key or settings.deepseek_api_key == "your_deepseek_api_key_here":
            logger.warning("DEEPSEEK_API_KEY 未配置，LLM 调用将失败。请在 backend/.env 填入真实 key。")
        _client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _client


def chat(messages: list[dict], temperature: float = 0.7, max_tokens: int | None = None) -> str:
    """非流式对话，返回完整文本。"""
    resp = get_client().chat.completions.create(
        model=settings.chat_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def chat_stream(messages: list[dict], temperature: float = 0.7) -> Iterator[str]:
    """流式对话，逐字 yield。"""
    stream = get_client().chat.completions.create(
        model=settings.chat_model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
