"""记忆库管理路由：L1-L6 的增删查。"""
from fastapi import APIRouter

from app.database import get_db
from app.services import memory
from app.models import ProfileItem, Fact, Preference

router = APIRouter()


# ===== L1 用户画像 =====

@router.get("/profile")
def get_profile():
    return memory.get_profile()


@router.post("/profile")
def set_profile(item: ProfileItem):
    memory.set_profile(item.key, item.value, item.confidence, item.source)
    return {"ok": True}


@router.delete("/profile/{key}")
def delete_profile(key: str):
    memory.delete_profile(key)
    return {"ok": True}


# ===== L2 关键事实 =====

@router.get("/facts")
def list_facts(category: str | None = None):
    return memory.list_facts(category)


@router.post("/facts")
def add_fact(fact: Fact):
    fid = memory.add_fact(fact.category, fact.content, fact.importance, fact.source)
    return {"id": fid}


@router.delete("/facts/{fid}")
def delete_fact(fid: str):
    memory.delete_fact(fid)
    return {"ok": True}


# ===== L3 偏好 =====

@router.get("/preferences")
def list_preferences(ptype: str | None = None):
    return memory.list_preferences(ptype)


@router.post("/preferences")
def add_preference(pref: Preference):
    pid = memory.add_preference(pref.type, pref.content, pref.importance)
    return {"id": pid}


@router.delete("/preferences/{pid}")
def delete_preference(pid: str):
    memory.delete_preference(pid)
    return {"ok": True}


# ===== L4 事件 =====

@router.get("/episodes")
def list_episodes(conversation_id: str | None = None, limit: int = 50):
    return memory.list_episodes(conversation_id, limit)


@router.delete("/episodes/{eid}")
def delete_episode(eid: str):
    memory.delete_episode(eid)
    return {"ok": True}


# ===== L5 反思 =====

@router.get("/reflections")
def list_reflections(rtype: str | None = None):
    return memory.list_reflections(rtype)


# ===== L6 认知框架（预置，只读） =====

@router.get("/frameworks")
def list_frameworks():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM frameworks ORDER BY type, name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
