"""对话引擎：上下文组装 + 反谄媚推理 + 认知框架调度 + 记忆提取。

反谄媚推理结构通过 system prompt 强制（先独立分析，再对比，再表达），
认知框架通过向量检索注入，记忆在对话后自动提取。
"""
import json as _json
import logging
from typing import Iterator, Optional

from app.services import llm, memory
from app.prompts.system import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# 上下文长度限制
MAX_RECENT_TURNS = 10          # 最近 N 轮对话（一轮 = user + assistant）
MAX_FACTS = 5
MAX_EPISODES = 3
MAX_FRAMEWORKS = 3


def chat_stream(
    conversation_id: Optional[str],
    user_message: str,
) -> tuple[str, Iterator[str]]:
    """主对话入口。

    返回 (conversation_id, 流式回复迭代器)。
    流式结束后自动保存 assistant 消息并提取记忆。
    """
    if not conversation_id:
        conversation_id = memory.create_conversation()

    # 存用户消息
    memory.add_message(conversation_id, "user", user_message)

    # 组装上下文
    messages = build_context(conversation_id, user_message)

    # 调用 LLM 流式，结束后保存
    def stream_and_save():
        full_reply = ""
        used_frameworks = [f.get("metadata", {}).get("name", "")
                           for f in messages[-1].get("_frameworks", [])] if False else []
        for chunk in llm.chat_stream(messages):
            full_reply += chunk
            yield chunk
        # 保存 assistant 消息
        memory.add_message(conversation_id, "assistant", full_reply)
        # 提取记忆（失败不阻塞）
        try:
            extract_and_store_memories(conversation_id, user_message, full_reply)
        except Exception as e:
            logger.warning("记忆提取失败: %s", e)

    return conversation_id, stream_and_save()


def build_context(conversation_id: str, user_message: str) -> list[dict]:
    """组装发送给 LLM 的 messages：system + 记忆 + 框架 + 历史。"""
    system = SYSTEM_PROMPT

    # L1 用户画像
    profile = memory.get_profile()
    if profile:
        profile_text = "\n".join(f"- {k}: {v['value']}" for k, v in profile.items())
        system += f"\n\n# 用户画像\n{profile_text}"

    # L2 相关关键事实
    facts = memory.search_facts(user_message, n=MAX_FACTS)
    if facts:
        facts_text = "\n".join(f"- {f['content']}" for f in facts)
        system += f"\n\n# 相关记忆（关键事实）\n{facts_text}"

    # L4 相关过往事件
    episodes = memory.search_episodes(user_message, n=MAX_EPISODES)
    if episodes:
        ep_text = "\n".join(f"- {e['content']}" for e in episodes)
        system += f"\n\n# 相关过往事件\n{ep_text}"

    # L6 认知框架（作为思考工具注入）
    frameworks = memory.search_frameworks(user_message, n=MAX_FRAMEWORKS)
    if frameworks:
        fw_lines = []
        for f in frameworks:
            name = f.get("metadata", {}).get("name", "")
            fw_lines.append(f"【{name}】{f['content']}")
        system += "\n\n# 可调用的认知框架（作为思考工具使用，不要背诵给用户）\n" + "\n".join(fw_lines)

    messages: list[dict] = [{"role": "system", "content": system}]

    # 对话历史（已包含刚存的当前 user message）
    history = memory.list_messages(conversation_id, limit=MAX_RECENT_TURNS * 2)
    for m in history:
        messages.append({"role": m["role"], "content": m["content"]})

    return messages


def extract_and_store_memories(conversation_id: str, user_message: str, assistant_reply: str) -> None:
    """从对话中提取关键事实并存入 L2。MVP1 用 LLM 提取。"""
    extract_prompt = (
        "从以下对话中提取值得长期记住的关键事实（关于用户本人的事实，不是闲聊内容）。\n"
        "只提取具体、持久、有价值的事实（如家庭情况、职业目标、重要关系、性格特点、关键经历）。\n"
        "不要提取临时情绪、一次性问题、AI的建议本身。\n"
        "如果没有值得提取的事实，返回空数组 []。\n\n"
        f"用户说: {user_message}\n"
        f"AI回复: {assistant_reply[:300]}\n\n"
        '以 JSON 数组返回，每项 {"category": "career|family|relationship|personality|goal|event|other", '
        '"content": "事实内容", "importance": 0.0-1.0}。\n'
        "只返回 JSON，不要其他文字。"
    )

    result = llm.chat(
        [{"role": "user", "content": extract_prompt}],
        temperature=0.1,
        max_tokens=500,
    )
    result = result.strip()
    if result.startswith("```"):
        # 去掉 ```json ... ``` 包裹
        parts = result.split("```")
        if len(parts) >= 2:
            result = parts[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
    facts = _json.loads(result)
    if not isinstance(facts, list):
        return
    for f in facts:
        if isinstance(f, dict) and f.get("content"):
            memory.add_fact(
                category=f.get("category", "other"),
                content=f["content"],
                importance=float(f.get("importance", 0.5)),
                source="extracted",
            )
            logger.info("提取事实: %s", str(f["content"])[:50])

    # 存 episode（本轮对话的事件记录）
    memory.add_episode(
        conversation_id=conversation_id,
        summary=user_message[:200],
        importance=0.5,
    )
