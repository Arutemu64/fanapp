import json

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from fanfan.application.sse.stream_events import StreamEvents

sse_router = APIRouter(tags=["SSE"])


@sse_router.get(
    "/events",
    summary="Stream events via SSE",
    description="Opens a Server-Sent Events connection to receive real-time event updates.",
    responses={
        200: {"description": "SSE stream established. Returns text/event-stream."},
    },
)
@inject
async def stream_events(
    request: Request,
    interactor: FromDishka[StreamEvents],
) -> StreamingResponse:

    async def event_generator():
        async for message in interactor():
            if await request.is_disconnected():
                break

            if message is None:
                yield ": keep-alive\n\n"
            else:
                yield f"event: {message.event_name}\ndata: {json.dumps(message.data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
