from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from autotube.infrastructure.config import RuntimeConfig
from autotube.infrastructure.db.database import Database
from autotube.infrastructure.runtime.worker_pool import WorkerPoolQueue
from autotube.infrastructure.youtube.gateway import GoogleYouTubeGateway
from autotube.infrastructure.youtube.settings import YouTubeSettings
from tests.unit.infrastructure.worker_pool_support import TIMEOUT, BlockingExecutor
from tests.unit.infrastructure.youtube_fakes import FakeService, media


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database(tmp_path / "test.db", RuntimeConfig().database_busy_timeout_ms)
    db.migrate()
    yield db
    db.dispose()


@pytest.fixture
def service() -> FakeService:
    return FakeService()


@pytest.fixture
def refreshed() -> list[str]:
    return []


@pytest.fixture
def gateway(service: FakeService, refreshed: list[str]) -> GoogleYouTubeGateway:
    return GoogleYouTubeGateway(
        YouTubeSettings(upload_chunk_bytes=256 * 1024, playlist_page_size=2),
        services=lambda _credentials: service,
        media=media,
        refresher=lambda credentials: refreshed.append(credentials.refresh_token or ""),
    )


@pytest.fixture
def executor() -> BlockingExecutor:
    return BlockingExecutor()


@pytest.fixture
def limit() -> list[int]:
    return [2]


@pytest.fixture
def pool(executor: BlockingExecutor, limit: list[int]) -> Iterator[WorkerPoolQueue]:
    queue = WorkerPoolQueue(lambda: limit[0], poll_seconds=0.01)
    queue.start(executor)
    yield queue
    executor.release.set()
    queue.stop(TIMEOUT)
