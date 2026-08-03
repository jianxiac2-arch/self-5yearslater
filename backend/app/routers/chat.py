"""对话路由：流式对话 + 会话历史。"""
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models import ChatRequest
from app.services import conversation, memory

router = APIRouter()


@router.post("/stream")
def chat_stream(req: ChatRequest):
    """流式对话。SSE 格式返回。"""
    conversation_id, stream = conversation.chat_stream(req.conversation_id, req.message)

    def generate():
        # 先发 conversation_id，让前端立刻拿到
        yield _sse({"conversation_id": conversation_id, "delta": "", "done": False})
        try:
            for chunk in stream:
                yield _sse({"delta": chunk, "done": False})
        except Exception as e:
            yield _sse({"delta": f"\n[出错: {e}]", "done": False})
        yield _sse({"delta": "", "done": True})

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/conversations")
def list_conversations():
    return memory.list_conversations()


@router.get("/conversations/{cid}/messages")
def get_messages(cid: str):
    return memory.list_messages(cid)


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"
