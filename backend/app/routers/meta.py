"""元认知路由：搜索 + 总结 + 站点元信息。"""
from fastapi import APIRouter

from app.config import settings
from app.models import SearchRequest, SummaryRequest
from app.services import meta, memory

router = APIRouter()


@router.get("/info")
def meta_info():
    """返回站点级元信息（演示 Case 名、是否启用口令等）。

    给前端显示标题用，避免前端硬编码「小林」等 case 名。
    """
    profile = memory.get_profile()
    demo_case_id = (profile.get("_demo_case_id") or {}).get("value") or ""
    demo_display_name = (
        (profile.get("_demo_case_display_name") or {}).get("value")
        or ("演示站点" if settings.seed_demo_data else "")
    )
    return {
        "auth_required": bool(settings.access_code),
        "seed_demo_data": settings.seed_demo_data,
        "demo_case_id": demo_case_id,
        "demo_case_display_name": demo_display_name,
    }


@router.post("/search")
def search(req: SearchRequest):
    hits = meta.search(req.query, layers=req.layers, limit=req.limit)
    return {"hits": hits}


@router.post("/summary")
def summary(req: SummaryRequest):
    text, rid = meta.summarize(req.dimension, req.value, req.save_as_reflection)
    return {"summary": text, "reflection_id": rid}

