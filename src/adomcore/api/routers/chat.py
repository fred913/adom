"""Chat router."""

import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from adomcore.api.schemas.chat import ChatRequest, ChatResponse
from adomcore.domain.ids import ThreadId

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    c = request.app.state.container
    result = await c.conversation_service.chat(
        req.text,
        ThreadId(req.thread_id) if req.thread_id else None,
    )
    return ChatResponse(
        response_text=result.response_text,
        thread_id=result.thread_id,
        steps=result.steps,
        tool_calls=result.tool_calls,
    )


@router.post("/stream")
async def chat_stream(req: ChatRequest, request: Request) -> StreamingResponse:
    c = request.app.state.container

    async def event_generator():
        async for event in c.conversation_service.chat_stream(
            req.text,
            ThreadId(req.thread_id) if req.thread_id else None,
        ):
            payload = json.dumps(event.data, ensure_ascii=False)
            yield f"event: {event.event}\ndata: {payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
