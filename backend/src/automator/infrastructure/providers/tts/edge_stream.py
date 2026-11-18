from __future__ import annotations

import asyncio
import importlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Protocol

from automator.shared.errors import UpstreamFailure

TICKS_PER_SECOND = 10_000_000


@dataclass(frozen=True)
class EdgeChunk:
    kind: str
    data: bytes = b""
    offset_seconds: float = 0.0
    duration_seconds: float = 0.0
    text: str = ""


class EdgeStream(Protocol):
    def stream(self, text: str, voice: str, rate: str) -> list[EdgeChunk]: ...


def as_chunk(raw: dict[str, Any]) -> EdgeChunk:
    if raw.get("type") == "audio":
        return EdgeChunk(kind="audio", data=bytes(raw.get("data", b"")))
    return EdgeChunk(
        kind=str(raw.get("type", "")),
        offset_seconds=float(raw.get("offset", 0)) / TICKS_PER_SECOND,
        duration_seconds=float(raw.get("duration", 0)) / TICKS_PER_SECOND,
        text=str(raw.get("text", "")),
    )


def communicator(module: Any, text: str, voice: str, rate: str) -> Any:
    try:
        return module.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    except TypeError:
        return module.Communicate(text, voice, rate=rate)


async def collect(text: str, voice: str, rate: str) -> list[EdgeChunk]:
    module: Any = importlib.import_module("edge_tts")
    communicate = communicator(module, text, voice, rate)
    return [as_chunk(raw) async for raw in communicate.stream()]


class EdgeTtsLibrary:
    def stream(self, text: str, voice: str, rate: str) -> list[EdgeChunk]:
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, collect(text, voice, rate)).result()
        except Exception as error:
            raise UpstreamFailure(f"edge-tts failed: {type(error).__name__}: {error}") from error
