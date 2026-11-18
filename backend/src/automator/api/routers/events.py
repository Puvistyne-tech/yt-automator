from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from automator.api.container import App, Options
from automator.api.event_stream import event_stream

router = APIRouter(tags=["events"])
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.get(
    "/events",
    response_class=StreamingResponse,
    summary="Server-sent events; each data line is a RunEvent",
)
async def events(app: App, options: Options) -> StreamingResponse:
    stream = event_stream(app.events.subscribe(), options.sse_heartbeat_seconds)
    return StreamingResponse(stream, media_type="text/event-stream", headers=STREAM_HEADERS)
