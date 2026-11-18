from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import AsyncGenerator, AsyncIterator
from pathlib import Path

from fastapi.testclient import TestClient

from automator.api.event_stream import HEARTBEAT_LINE, event_stream
from automator.domain.run_enums import RunEventKind
from automator.domain.runs import RunEvent
from automator.infrastructure.config import RuntimeConfig
from automator.main import Overrides, create_app
from tests.fixtures.fake_runtime import START, RecordingEvents
from tests.unit.api.client import Api, error_of

EVENT = RunEvent(run_id="r1", kind=RunEventKind.STATUS, at=START, payload={"status": "running"})


def test_unknown_routes_and_bad_json_use_the_error_envelope(api: Api) -> None:
    assert error_of(api.client.get("/api/nope"), 404)["code"] == "not_found"
    response = api.client.post(
        "/api/credentials", content=b"{bad", headers={"content-type": "application/json"}
    )
    assert error_of(response, 400)["code"] == "validation_failed"


def test_event_route_streams_run_events(config: RuntimeConfig, overrides: Overrides) -> None:
    events = RecordingEvents()
    events.publish(EVENT)
    app = create_app(config, Overrides(**(vars(overrides) | {"events": events})))
    with TestClient(app) as client, client.stream("GET", "/api/events") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        lines = [line for line in response.iter_lines() if line.startswith("data: ")]
    assert [json.loads(line.removeprefix("data: ")) for line in lines] == [
        EVENT.model_dump(mode="json")
    ]


async def silent_then_event() -> AsyncIterator[RunEvent]:
    await asyncio.sleep(0.05)
    yield EVENT
    await asyncio.sleep(10)
    yield EVENT


def test_stream_sends_heartbeats_and_closes_its_source() -> None:
    source = silent_then_event()
    assert isinstance(source, AsyncGenerator)

    async def scenario() -> list[str]:
        stream = event_stream(source, heartbeat_seconds=0.01)
        chunks: list[str] = []
        while not chunks or not chunks[-1].startswith("data: "):
            chunks.append(await anext(stream))
        await stream.aclose()  # type: ignore[attr-defined]
        return chunks

    chunks = asyncio.run(scenario())
    assert HEARTBEAT_LINE in chunks
    assert chunks[-1] == f"data: {EVENT.model_dump_json()}\n\n"
    assert inspect.getasyncgenstate(source) == inspect.AGEN_CLOSED


def test_built_web_ui_is_served_with_spa_fallback(
    config: RuntimeConfig, overrides: Overrides, tmp_path: Path
) -> None:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("js", encoding="utf-8")
    app = create_app(config.model_copy(update={"web_dist_dir": dist}), overrides)
    with TestClient(app) as client:
        assert client.get("/").text == "<html>app</html>"
        assert client.get("/assets/app.js").text == "js"
        assert client.get("/runs/abc").text == "<html>app</html>"
        assert client.get("/api/health").json()["status"] == "ok"
        assert error_of(client.get("/api/unknown"), 404)["code"] == "not_found"


def test_cors_allows_the_vite_origin(api: Api) -> None:
    response = api.client.options(
        "/api/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
