"""元认知路由：搜索 + 总结。"""
from fastapi import APIRouter

from app.models import SearchRequest, SummaryRequest
from app.services import meta

router = APIRouter()


@router.post("/search")
def search(req: SearchRequest):
    hits = meta.search(req.query, layers=req.layers, limit=req.limit)
    return {"hits": hits}


@router.post("/summary")
def summary(req: SummaryRequest):
    text, rid = meta.summarize(req.dimension, req.value, req.save_as_reflection)
    return {"summary": text, "reflection_id": rid}
