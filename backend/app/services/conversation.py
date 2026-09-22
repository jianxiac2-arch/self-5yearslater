"""对话引擎：Counterpart 核心引擎 —— 上下文组装 + 防带偏推理 + 认知框架调度 + 记忆提取。

防带偏推理结构通过 system prompt 强制（先独立分析，再对比，再表达），
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
MAX_PREFERENCES = 10
MAX_REFLECTIONS = 3
MAX_EPISODES = 3
MAX_FRAMEWORKS = 3

# 相似度阈值：score = 1 - cosine_distance，低于此值不注入（避免硬塞低相关记忆）
MIN_RELEVANCE_SCORE = 0.42

# 闲聊识别关键词：消息含这些词或纯短句时，跳过 L2/L4/L5/L6 检索，只注入 L1 画像
_CASUAL_PATTERNS = [
    "吃什么", "今天吃", "晚饭", "午饭", "早饭", "想吃什么",
    "几点了", "天气", "你好", "在吗", "哈喽", "嗨",
    "晚安", "早安", "拜拜", "再见",
    "谢谢", "感谢", "辛苦",
]


def _is_casual(message: str) -> bool:
    """判断是否是闲聊/日常问题——这类问题不需要检索历史记忆。

    判断规则：
    1. 消息很短（< 12 字）且不含决策/纠结关键词
    2. 命中闲聊关键词模式
    3. 不含"我该不该 / 怎么办 / 纠结 / 选择"等深度决策信号
    """
    msg = message.strip()
    if not msg:
        return True
    # 决策/纠结信号 → 不是闲聊
    deep_signals = ["怎么办", "该不该", "该不该", "纠结", "选择", "决定", "要不要", "职业", "工作",
                   "转行", "辞职", "分手", "结婚", "事业", "未来", "方向", "迷茫", "焦虑"]
    if any(s in msg for s in deep_signals):
        return False
    # 命中闲聊关键词
    if any(p in msg for p in _CASUAL_PATTERNS):
        return True
    # 短消息且不含深度信号 → 闲聊
    if len(msg) < 12:
        return True
    return False


def _filter_relevant(hits: list[dict], min_score: float = MIN_RELEVANCE_SCORE) -> list[dict]:
    """过滤低相关度的检索结果。score 字段来自 1 - cosine_distance。"""
    return [h for h in hits if h.get("score") is not None and h["score"] >= min_score]


def chat_stream(
    conversation_id: Optional[str],
    user_message: str,
) -> tuple[str, Iterator[str]]:
    """主对话入口：盲评双调用 + 流式输出。

    Call #1（盲）：剥掉用户立场，独立分析，输出结构化结论。
    Call #2（明）：基于盲评结论 + 用户原始立场，流式输出对比表达。
    流式结束后自动保存 assistant 消息并提取记忆。
    """
    if not conversation_id:
        conversation_id = memory.create_conversation()

    # 存用户消息
    memory.add_message(conversation_id, "user", user_message)

    # 组装基础上下文（system + 记忆 + 框架 + 历史）
    messages = build_context(conversation_id, user_message)
    system_prompt = messages[0]["content"]

    # Call #1：盲评——独立分析（看不到"该附和谁"的压力）
    blind_result = blind_analyze(system_prompt, user_message)
    logger.info("盲评结论: stance=%s confidence=%.2f", blind_result.get("stance"), blind_result.get("confidence", 0))

    # 将盲评结论注入 system prompt，供 Call #2 做对比表达
    if blind_result:
        conclusion_text = (
            f"\n\n# 独立分析结论（盲评，已剥离用户立场）\n"
            f"立场倾向: {blind_result.get('stance', 'uncertain')}（agree=认同用户 / disagree=不同意 / uncertain=不确定）\n"
            f"独立结论: {blind_result.get('independent_conclusion', '')}\n"
            f"关键假设: {blind_result.get('key_assumptions', '')}\n"
            f"信心度: {blind_result.get('confidence', 0)}\n\n"
            f"请基于以上独立分析结论，对比用户的原始观点，给出诚实表达。"
            f"如果独立分析认同用户，直接认同不用客套；如果不同意，明确说不同意并给理由；不要用'你说得对，但是…'句式。"
        )
        messages[0]["content"] = system_prompt + conclusion_text

    # Call #2：流式输出最终回复
    def stream_and_save():
        full_reply = ""
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


def blind_analyze(system_prompt: str, user_message: str) -> dict:
    """Call #1 盲评：让模型在看不到用户立场的情况下独立分析。

    把用户消息改写为中立情境，要求模型输出结构化结论：
    {stance, independent_conclusion, confidence, key_assumptions}
    失败时返回空 dict，Call #2 降级为单次调用。
    """
    blind_prompt = (
        "你是一个独立分析者。请抛开用户可能持有的任何立场，纯粹基于事实和逻辑分析下面这个问题。\n"
        "不要考虑用户希望听到什么，只给出你认为最接近真相的判断。\n\n"
        f"问题：{user_message}\n\n"
        "请以 JSON 格式返回，包含以下字段：\n"
        '- "stance": "agree" | "disagree" | "uncertain" —— 如果你是用户，你会认同这个方向吗？\n'
        '- "independent_conclusion": 一句话独立结论\n'
        '- "confidence": 0.0-1.0 的信心度\n'
        '- "key_assumptions": 结论依赖的关键假设（2-3 条）\n'
        "只返回 JSON，不要其他文字。"
    )
    try:
        result = llm.chat(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": blind_prompt}],
            temperature=0.3,
            max_tokens=600,
        )
        result = result.strip()
        if result.startswith("```"):
            parts = result.split("```")
            if len(parts) >= 2:
                result = parts[1]
                if result.startswith("json"):
                    result = result[4:]
            result = result.strip()
        import json as _json
        parsed = _json.loads(result)
        if isinstance(parsed, dict):
            return parsed
    except Exception as e:
        logger.warning("盲评调用失败，降级为单次调用: %s", e)
    return {}


def build_context(conversation_id: str, user_message: str) -> list[dict]:
    """组装发送给 LLM 的 messages：system + 记忆 + 框架 + 历史。

    优化（防止"硬塞记忆"）：
    1. 闲聊识别——日常问题只注入 L1 画像，跳过 L2/L4/L5/L6 检索
    2. 相似度阈值——非闲聊也只注入 score >= MIN_RELEVANCE_SCORE 的高相关结果
    """
    system = SYSTEM_PROMPT

    # L1 用户画像（始终注入——基础身份信息）
    profile = memory.get_profile()
    if profile:
        profile_text = "\n".join(f"- {k}: {v['value']}" for k, v in profile.items())
        system += f"\n\n# 用户画像\n{profile_text}"

    # 闲聊短路：日常问题（"今晚吃什么"等）跳过深度检索
    is_casual = _is_casual(user_message)
    if is_casual:
        logger.info("识别为闲聊，跳过 L2/L4/L5/L6 检索: %s", user_message[:30])
        messages: list[dict] = [{"role": "system", "content": system}]
        history = memory.list_messages(conversation_id, limit=MAX_RECENT_TURNS * 2)
        for m in history:
            messages.append({"role": m["role"], "content": m["content"]})
        return messages

    # L3 偏好（始终注入——用于建议落地性检验，量小不影响）
    preferences = memory.list_preferences()
    if preferences:
        pref_lines = []
        for p in preferences:
            label = {"like": "喜欢", "dislike": "反感", "style": "风格", "taboo": "禁忌"}.get(p["type"], p["type"])
            pref_lines.append(f"- [{label}] {p['content']}")
        system += "\n\n# 用户偏好（用于建议落地性检验，不要硬塞给用户）\n" + "\n".join(pref_lines)

    # L2 相关关键事实（加相似度过滤）
    facts = _filter_relevant(memory.search_facts(user_message, n=MAX_FACTS))
    if facts:
        facts_text = "\n".join(f"- {f['content']}" for f in facts)
        system += f"\n\n# 相关记忆（关键事实，仅高相关）\n{facts_text}"

    # L5 反思（模式/趋势/盲点——5 年视角的核心知识来源，加相似度过滤）
    reflections = _filter_relevant(memory.search_reflections(user_message, n=MAX_REFLECTIONS))
    if reflections:
        ref_lines = []
        for r in reflections:
            rtype = r.get("metadata", {}).get("type", "reflection")
            type_label = {"pattern": "模式", "trend": "趋势", "blindspot": "盲点", "change": "变化"}.get(rtype, rtype)
            ref_lines.append(f"- [{type_label}] {r['content']}")
        system += "\n\n# 深层反思（用户自己的模式/趋势/盲点，仅高相关，作为 5 年视角的推演依据）\n" + "\n".join(ref_lines)

    # L4 相关过往事件（加相似度过滤）
    episodes = _filter_relevant(memory.search_episodes(user_message, n=MAX_EPISODES))
    if episodes:
        ep_text = "\n".join(f"- {e['content']}" for e in episodes)
        system += f"\n\n# 相关过往事件（仅高相关）\n{ep_text}"

    # L6 认知框架（作为思考工具注入，加相似度过滤）
    frameworks = _filter_relevant(memory.search_frameworks(user_message, n=MAX_FRAMEWORKS))
    if frameworks:
        fw_lines = []
        for f in frameworks:
            name = f.get("metadata", {}).get("name", "")
            fw_lines.append(f"【{name}】{f['content']}")
        system += "\n\n# 可调用的认知框架（作为思考工具使用，不要背诵给用户）\n" + "\n".join(fw_lines)

    messages = [{"role": "system", "content": system}]

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
