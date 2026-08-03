"""记忆库服务：分层记忆的 CRUD、语义检索、重要性管理。

分层（对应 spec 第 2.1 节）：
- L1 profile: 用户画像（结构化）
- L2 facts: 关键事实（结构化 + 向量）
- L3 preferences: 偏好（结构化）
- L4 episodes: 事件/对话记录（向量 + 元数据）
- L5 reflections: 反思（结构化 + 向量）
- L6 frameworks: 认知框架（由 seed.py 预置，这里只读检索）
"""
import json
import uuid
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.vector_store import (
    get_collection,
    COLLECTION_FACTS,
    COLLECTION_EPISODES,
    COLLECTION_REFLECTIONS,
    COLLECTION_FRAMEWORKS,
)


# ===== L1 用户画像 =====

def get_profile() -> dict:
    """返回 {key: {value, confidence, source, updated_at}}。"""
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM profile").fetchall()
        return {r["key"]: dict(r) for r in rows}
    finally:
        conn.close()


def set_profile(key: str, value: str, confidence: Optional[float] = None, source: str = "manual") -> None:
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO profile (key, value, confidence, source, updated_at) VALUES (?,?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, confidence=excluded.confidence, "
            "source=excluded.source, updated_at=excluded.updated_at",
            (key, value, confidence, source, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def delete_profile(key: str) -> None:
    conn = get_db()
    try:
        conn.execute("DELETE FROM profile WHERE key=?", (key,))
        conn.commit()
    finally:
        conn.close()


# ===== L2 关键事实 =====

def add_fact(category: str, content: str, importance: float = 0.5, source: str = "extracted") -> str:
    fid = str(uuid.uuid4())
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO facts (id, category, content, importance, source) VALUES (?,?,?,?,?)",
            (fid, category, content, importance, source),
        )
        conn.commit()
    finally:
        conn.close()
    get_collection(COLLECTION_FACTS).add(
        ids=[fid],
        documents=[content],
        metadatas=[{"category": category, "importance": importance}],
    )
    return fid


def list_facts(category: Optional[str] = None) -> list[dict]:
    conn = get_db()
    try:
        if category:
            rows = conn.execute(
                "SELECT * FROM facts WHERE category=? ORDER BY importance DESC", (category,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM facts ORDER BY importance DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_fact_importance(fid: str, importance: float) -> None:
    conn = get_db()
    try:
        conn.execute(
            "UPDATE facts SET importance=?, updated_at=? WHERE id=?",
            (importance, datetime.now().isoformat(), fid),
        )
        conn.commit()
    finally:
        conn.close()


def delete_fact(fid: str) -> None:
    conn = get_db()
    try:
        conn.execute("DELETE FROM facts WHERE id=?", (fid,))
        conn.commit()
    finally:
        conn.close()
    try:
        get_collection(COLLECTION_FACTS).delete(ids=[fid])
    except Exception:
        pass


# ===== L3 偏好 =====

def add_preference(ptype: str, content: str, importance: float = 0.5) -> str:
    pid = str(uuid.uuid4())
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO preferences (id, type, content, importance) VALUES (?,?,?,?)",
            (pid, ptype, content, importance),
        )
        conn.commit()
    finally:
        conn.close()
    return pid


def list_preferences(ptype: Optional[str] = None) -> list[dict]:
    conn = get_db()
    try:
        if ptype:
            rows = conn.execute("SELECT * FROM preferences WHERE type=?", (ptype,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM preferences").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_preference(pid: str) -> None:
    conn = get_db()
    try:
        conn.execute("DELETE FROM preferences WHERE id=?", (pid,))
        conn.commit()
    finally:
        conn.close()


# ===== L4 事件 =====

def add_episode(
    conversation_id: Optional[str],
    summary: str,
    importance: float = 0.5,
    topics: Optional[list] = None,
    entities: Optional[list] = None,
) -> str:
    eid = str(uuid.uuid4())
    topics = topics or []
    entities = entities or []
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO episodes (id, conversation_id, summary, importance, topics, entities, occurred_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (eid, conversation_id, summary, importance,
             json.dumps(topics, ensure_ascii=False),
             json.dumps(entities, ensure_ascii=False),
             datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    get_collection(COLLECTION_EPISODES).add(
        ids=[eid],
        documents=[summary],
        metadatas=[{"conversation_id": conversation_id or "", "importance": importance}],
    )
    return eid


def list_episodes(conversation_id: Optional[str] = None, limit: int = 50) -> list[dict]:
    conn = get_db()
    try:
        if conversation_id:
            rows = conn.execute(
                "SELECT * FROM episodes WHERE conversation_id=? ORDER BY occurred_at DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM episodes ORDER BY occurred_at DESC LIMIT ?", (limit,)
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["topics"] = json.loads(d["topics"]) if d["topics"] else []
            d["entities"] = json.loads(d["entities"]) if d["entities"] else []
            result.append(d)
        return result
    finally:
        conn.close()


def delete_episode(eid: str) -> None:
    conn = get_db()
    try:
        conn.execute("DELETE FROM episodes WHERE id=?", (eid,))
        conn.commit()
    finally:
        conn.close()
    try:
        get_collection(COLLECTION_EPISODES).delete(ids=[eid])
    except Exception:
        pass


# ===== L5 反思 =====

def add_reflection(rtype: str, content: str, evidence: Optional[list] = None) -> str:
    rid = str(uuid.uuid4())
    evidence = evidence or []
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO reflections (id, type, content, evidence) VALUES (?,?,?,?)",
            (rid, rtype, content, json.dumps(evidence, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()
    get_collection(COLLECTION_REFLECTIONS).add(
        ids=[rid], documents=[content], metadatas=[{"type": rtype}]
    )
    return rid


def list_reflections(rtype: Optional[str] = None) -> list[dict]:
    conn = get_db()
    try:
        if rtype:
            rows = conn.execute("SELECT * FROM reflections WHERE type=?", (rtype,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM reflections ORDER BY created_at DESC").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["evidence"] = json.loads(d["evidence"]) if d["evidence"] else []
            result.append(d)
        return result
    finally:
        conn.close()


# ===== 语义检索 =====

def search_facts(query: str, n: int = 5) -> list[dict]:
    return _query_collection(COLLECTION_FACTS, query, n, "facts")


def search_episodes(query: str, n: int = 5) -> list[dict]:
    return _query_collection(COLLECTION_EPISODES, query, n, "episodes")


def search_reflections(query: str, n: int = 3) -> list[dict]:
    return _query_collection(COLLECTION_REFLECTIONS, query, n, "reflections")


def search_frameworks(query: str, n: int = 3) -> list[dict]:
    return _query_collection(COLLECTION_FRAMEWORKS, query, n, "frameworks")


def search_all(query: str, layers: Optional[list] = None, n_per_layer: int = 5) -> list[dict]:
    """跨层搜索。layers 为空则搜全部。返回按相关度排序的结果。"""
    layer_map = {
        "facts": COLLECTION_FACTS,
        "episodes": COLLECTION_EPISODES,
        "reflections": COLLECTION_REFLECTIONS,
        "frameworks": COLLECTION_FRAMEWORKS,
    }
    target_layers = layers or list(layer_map.keys())
    hits = []
    for layer in target_layers:
        if layer in layer_map:
            hits.extend(_query_collection(layer_map[layer], query, n_per_layer, layer))
    hits.sort(key=lambda x: x.get("score", 0) or 0, reverse=True)
    return hits


def _query_collection(collection_name: str, query: str, n: int, layer: str) -> list[dict]:
    coll = get_collection(collection_name)
    res = coll.query(query_texts=[query], n_results=n)
    return _format_results(res, layer)


def _format_results(res: dict, layer: str) -> list[dict]:
    hits = []
    if not res.get("ids") or not res["ids"][0]:
        return hits
    ids = res["ids"][0]
    docs = res.get("documents", [[]])[0]
    dists = res.get("distances", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    for i, _id in enumerate(ids):
        hits.append({
            "layer": layer,
            "id": _id,
            "content": docs[i] if i < len(docs) else "",
            "score": (1 - dists[i]) if i < len(dists) and dists[i] is not None else None,
            "metadata": metas[i] if i < len(metas) else {},
        })
    return hits


# ===== 对话记录 =====

def create_conversation(title: str = "") -> str:
    cid = str(uuid.uuid4())
    conn = get_db()
    try:
        conn.execute("INSERT INTO conversations (id, title) VALUES (?,?)", (cid, title))
        conn.commit()
    finally:
        conn.close()
    return cid


def add_message(conversation_id: str, role: str, content: str, metadata: Optional[dict] = None) -> str:
    mid = str(uuid.uuid4())
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, metadata) VALUES (?,?,?,?,?)",
            (mid, conversation_id, role, content,
             json.dumps(metadata, ensure_ascii=False) if metadata else None),
        )
        conn.commit()
    finally:
        conn.close()
    return mid


def list_messages(conversation_id: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_conversations(limit: int = 50) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
