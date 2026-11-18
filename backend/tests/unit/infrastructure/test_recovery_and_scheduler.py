from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

import pytest

from automator.domain.run_enums import RunStatus, StageStatus, UploadStatus
from automator.domain.run_parts import StageRun, Upload
from automator.infrastructure.config import RuntimeConfig, SecretBackend, load_config
from automator.infrastructure.runtime.recovery import recover_interrupted_runs
from automator.infrastructure.runtime.scheduler import SchedulerTicker
from tests.fixtures.fake_repositories import InMemoryRuns
from tests.fixtures.fake_runtime import FakeClock, RecordingQueue
from tests.unit.infrastructure.records import run


def upload(status: UploadStatus) -> Upload:
    return Upload(target_id="t", channel_id="c", language="en", variant="v", status=status)


def test_recovery_fails_interrupted_runs_and_requeues_queued_ones() -> None:
    runs, queue, clock = InMemoryRuns(), RecordingQueue(), FakeClock()
    busy_stage = StageRun(stage_id="render", title="Render", status=StageStatus.RUNNING)
    runs.save(run("running", 1, status=RunStatus.RUNNING, stages=(busy_stage,)))
    uploads = (upload(UploadStatus.DONE), upload(UploadStatus.UPLOADING))
    runs.save(run("publishing", 2, status=RunStatus.PUBLISHING, uploads=uploads))
    runs.save(run("queued-late", 4))
    runs.save(run("queued-early", 3))
    runs.save(run("waiting", 5, status=RunStatus.AWAITING_REVIEW))
    report = recover_interrupted_runs(runs, queue, clock)
    assert sorted(report.failed) == ["publishing", "running"]
    assert queue.enqueued == ["queued-early", "queued-late"]
    crashed = runs.items["running"]
    assert crashed.status is RunStatus.FAILED
    assert crashed.error is not None and "interrupted" in crashed.error
    assert crashed.finished_at == clock.now()
    assert crashed.stages[0].status is StageStatus.FAILED
    statuses = [item.status for item in runs.items["publishing"].uploads]
    assert statuses == [UploadStatus.DONE, UploadStatus.FAILED]
    assert runs.items["waiting"].status is RunStatus.AWAITING_REVIEW


def test_scheduler_ticks_with_the_clock_and_survives_errors() -> None:
    clock = FakeClock()
    seen: list[datetime] = []
    ticked = threading.Event()

    def tick(now: datetime) -> None:
        seen.append(now)
        if len(seen) >= 2:
            ticked.set()
        if len(seen) == 1:
            raise RuntimeError("tick failed")

    ticker = SchedulerTicker(tick, clock, interval_seconds=0.01)
    ticker.tick_once()
    ticker.start()
    assert ticked.wait(5)
    ticker.stop(5)
    assert len(seen) >= 2
    assert seen[0] == clock.now()
    assert ticker.thread is not None and not ticker.thread.is_alive()


def test_config_reads_prefixed_environment(tmp_path: Path) -> None:
    config = load_config(
        {
            "AUTOMATOR_DATA_DIR": str(tmp_path),
            "AUTOMATOR_PORT": "9000",
            "AUTOMATOR_SECRET_BACKEND": "file",
            "AUTOMATOR_RELOAD": "true",
            "AUTOMATOR_CORS_ORIGINS": "http://a, http://b",
            "AUTOMATOR_REDIRECT_BASE_URL": "http://host:1/",
            "UNRELATED": "x",
        }
    )
    assert (config.data_dir, config.port, config.reload) == (tmp_path, 9000, True)
    assert config.secret_backend is SecretBackend.FILE
    assert config.cors_origins == ("http://a", "http://b")
    assert config.oauth_redirect_uri == "http://host:1/api/oauth/callback"
    assert config.database_path == tmp_path / "automator.db"


def test_config_defaults_and_validation() -> None:
    config = RuntimeConfig()
    assert config.oauth_redirect_uri == "http://127.0.0.1:8000/api/oauth/callback"
    assert config.secret_backend is SecretBackend.AUTO
    with pytest.raises(ValueError, match="port"):
        load_config({"AUTOMATOR_PORT": "0"})
