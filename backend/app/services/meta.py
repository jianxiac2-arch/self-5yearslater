"""元认知服务：对记忆库的搜索、总结、分析。

让用户能"思考自己的思考"——查询和总结自己的历史。
"""
import logging
from typing import Optional

from app.services import llm, memory

logger = logging.getLogger(__name__)


def search(query: str, layers: Optional[list] = None, limit: int = 10) -> list[dict]:
    """跨层语义搜索记忆。"""
    return memory.search_all(query, layers=layers, n_per_layer=limit)


def summarize(dimension: str, value: str, save_as_reflection: bool = False) -> tuple[str, Optional[str]]:
    """按维度总结记忆。

    dimension: time | topic | person
    value: 具体值（如"过去一个月" / "职业选择" / "某人物名"）
    返回 (总结文本, reflection_id 或 None)。
    """
    material = _collect_material(dimension, value)
    if not material.strip():
        return "没有找到相关的记忆。", None

    if dimension == "time":
        prompt = (
            f"以下是用户最近的主要对话记录。请总结：\n{material}\n\n"
            "给出简洁总结，包括：主要关注的话题、情绪倾向、反复出现的模式、可能的变化趋势。"
        )
    elif dimension == "topic":
        prompt = (
            f"用户想回顾「关于{value}我说过什么」。基于以下相关记忆给出总结：\n{material}\n\n"
            "梳理用户在这个主题上的观点、变化、纠结点。"
        )
    elif dimension == "person":
        prompt = (
            f"用户想回顾「关于{value}我提到过什么」。基于以下相关记忆给出总结：\n{material}\n\n"
            "梳理用户和这个人的关系、互动、情感变化。"
        )
    else:
        return "不支持的维度（支持 time/topic/person）。", None

    summary_text = llm.chat([{"role": "user", "content": prompt}], temperature=0.3)

    reflection_id = None
    if save_as_reflection and summary_text:
        reflection_id = memory.add_reflection("pattern", summary_text)
    return summary_text, reflection_id


def _collect_material(dimension: str, value: str) -> str:
    """根据维度收集总结素材。"""
    lines = []
    if dimension == "time":
        # 按时间取最近的 episodes
        episodes = memory.list_episodes(limit=60)
        for e in episodes:
            lines.append(f"- {e['summary']}")
    else:
        # topic / person 用语义检索
        hits = memory.search_all(value, n_per_layer=10)
        for h in hits:
            lines.append(f"- [{h['layer']}] {h['content']}")
    return "\n".join(lines)
