"""把预置数据写入数据库。

首次运行或更新认知框架时执行：
    python -m app.seed

设 SEED_DEMO_DATA=true 时，同时写入半虚拟演示人格（公网 demo 用，仅职业/学业向）。
"""
import logging

from app.config import settings
from app.database import get_db, init_db
from app.vector_store import (
    get_collection,
    COLLECTION_FRAMEWORKS,
    COLLECTION_FACTS,
    COLLECTION_EPISODES,
    COLLECTION_REFLECTIONS,
)
from app.prompts.frameworks import ALL_FRAMEWORKS
from app.services import memory

logger = logging.getLogger("5yl.seed")

# 演示数据版本标记：改了演示内容就升版本号，重置/重布时会刷新
DEMO_MARKER_KEY = "_demo_seed_version"
DEMO_VERSION = "v1"

# ===== 演示人格：虚构用户「小林」，仅职业/学业向，不含真实隐私 =====

DEMO_PROFILE: dict[str, str] = {
    "年龄": "24 岁",
    "身份": "心理学硕士研三，正在秋招求职",
    "性格": "内向（I 人），偏好深度思考与书面表达，不擅长主动社交和在人群中自夸",
    "职业方向": "AI 产品经理（C 端方向）",
    "长期目标": "5 年内成为能独立负责 AI 产品 0→1 的产品经理；把心理学背景转化为产品上的差异化能力",
    "价值观": "诚实比好听重要；看重长期成长而非短期 title；决策习惯先自己分析再听意见",
    "数据说明": "本画像为演示用虚构数据，便于访客直接体验记忆与视角效果",
}

DEMO_FACTS: list[tuple[str, str, float]] = [
    ("career", "有三段实习：美团金融产品经理实习、字节跳动 AI 直播审核方向产品运营、科大讯飞 AI 心理健康产品助理", 0.9),
    ("career", "正在投递腾讯 AI 产品经理培训生（金融 AI Agent 方向）等秋招岗位", 0.85),
    ("event", "之前的产品岗面试因 C 端基本功不足（需求拆解、AB 测试、漏斗分析）被挂过，一直有心理阴影", 0.9),
    ("event", "最近独立做了一个个人 AI Agent 项目「5 年后的我」：分层记忆库 + 反谄媚推理，准备写进简历", 0.85),
    ("goal", "毕业论文用中介模型做统计分析，熟悉 SPSS 和 Hayes PROCESS macro", 0.7),
    ("personality", "习惯用做项目和作品来证明自己，不擅长在面试中直接推销自己", 0.8),
    ("goal", "纠结过是否读博，最终确定先就业、在产业里做 AI 产品", 0.6),
]

DEMO_REFLECTIONS: list[tuple[str, str]] = [
    ("pattern", "反复在「实习经历不够硬核」和「C 端基本功不足」两点上焦虑，但应对模式始终没变：用做具体项目来对冲不确定性。焦虑主题重复出现，行动路径单一。"),
    ("trend", "话题重心已从「要不要投产品岗」转向「怎么把项目讲清楚、怎么准备面试」——方向已定，当前瓶颈在表达与包装，而非选择本身。"),
]


def seed_frameworks() -> int:
    """写入/更新 L6 认知框架。返回写入条数。

    只覆盖预置条目（按 id 匹配），用户自定义的框架不受影响。
    """
    init_db()
    conn = get_db()
    try:
        coll = get_collection(COLLECTION_FRAMEWORKS)
        preset_ids = [fw["id"] for fw in ALL_FRAMEWORKS]

        # 清空旧的预置框架（SQLite + 向量库同步）
        placeholders = ",".join("?" * len(preset_ids))
        conn.execute(f"DELETE FROM frameworks WHERE id IN ({placeholders})", preset_ids)
        existing = coll.get(ids=preset_ids)
        if existing and existing["ids"]:
            coll.delete(ids=existing["ids"])

        # 写入新的
        for fw in ALL_FRAMEWORKS:
            conn.execute(
                "INSERT INTO frameworks (id, type, name, content, trigger_conditions, vector_id) "
                "VALUES (?,?,?,?,?,?)",
                (fw["id"], fw["type"], fw["name"], fw["content"], fw["trigger_conditions"], fw["id"]),
            )
            coll.add(
                ids=[fw["id"]],
                documents=[f"{fw['name']}。{fw['content']}。触发：{fw['trigger_conditions']}"],
                metadatas=[{"type": fw["type"], "name": fw["name"]}],
            )
        conn.commit()
        return len(ALL_FRAMEWORKS)
    finally:
        conn.close()


def seed_demo_data(force: bool = False) -> int:
    """写入演示人格（L1 + L2 + L5）。幂等：同版本已写入则跳过。

    force=True 时先清掉旧演示条目再写入。
    """
    init_db()
    profile = memory.get_profile()
    marker = profile.get(DEMO_MARKER_KEY, {}).get("value")
    if marker == DEMO_VERSION and not force:
        logger.info("演示数据 %s 已存在，跳过。", DEMO_VERSION)
        return 0

    # L1
    for key, value in DEMO_PROFILE.items():
        memory.set_profile(key, value, source="manual")
    memory.set_profile(DEMO_MARKER_KEY, DEMO_VERSION, source="manual")

    # L2
    for category, content, importance in DEMO_FACTS:
        memory.add_fact(category=category, content=content, importance=importance, source="manual")

    # L5
    for rtype, content in DEMO_REFLECTIONS:
        memory.add_reflection(rtype=rtype, content=content)

    logger.info("演示数据已写入：%d 条画像，%d 条事实，%d 条反思。",
                len(DEMO_PROFILE) + 1, len(DEMO_FACTS), len(DEMO_REFLECTIONS))
    return len(DEMO_FACTS)


def _clear_vector_collection(name: str) -> None:
    try:
        coll = get_collection(name)
        existing = coll.get()
        if existing and existing.get("ids"):
            coll.delete(ids=existing["ids"])
    except Exception as e:
        logger.warning("清空向量集合 %s 失败: %s", name, e)


def reset_demo_data() -> None:
    """清空所有用户数据（保留服务本身），重建框架 + 演示人格。

    供公网 demo「恢复演示数据」使用；对应 POST /api/admin/reset-demo。
    """
    init_db()
    conn = get_db()
    try:
        for table in ("messages", "episodes", "facts", "reflections",
                      "preferences", "conversations", "profile"):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        conn.close()

    for name in (COLLECTION_FACTS, COLLECTION_EPISODES, COLLECTION_REFLECTIONS):
        _clear_vector_collection(name)

    seed_frameworks()
    seed_demo_data(force=True)
    logger.info("演示环境已重置。")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    n = seed_frameworks()
    print(f"已写入 {n} 条认知框架。")
    if settings.seed_demo_data:
        seed_demo_data()
        print("演示数据已就绪。")
