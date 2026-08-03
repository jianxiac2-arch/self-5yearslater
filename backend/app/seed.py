"""把预置数据写入数据库。

首次运行或更新认知框架时执行：
    python -m app.seed
"""
from app.database import get_db, init_db
from app.vector_store import get_collection, COLLECTION_FRAMEWORKS
from app.prompts.frameworks import ALL_FRAMEWORKS


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


if __name__ == "__main__":
    n = seed_frameworks()
    print(f"已写入 {n} 条认知框架。")
