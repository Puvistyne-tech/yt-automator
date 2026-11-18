from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from automator.domain.run_enums import RunStatus
from automator.infrastructure.config import RuntimeConfig
from automator.main import Overrides, Runtime, create_app, youtube_gateway
from tests.unit.api.client import Api
from tests.unit.infrastructure.records import run


def test_youtube_settings_come_from_the_runtime_config() -> None:
    config = RuntimeConfig(
        youtube_caption_track_name="English",
        youtube_playlist_page_size=10,
        upload_chunk_bytes=512 * 1024,
    )
    settings = youtube_gateway(config).settings
    assert (settings.caption_track_name, settings.playlist_page_size) == ("English", 10)
    assert settings.upload_chunk_bytes == 512 * 1024
    assert settings.redirect_uri == config.oauth_redirect_uri


def test_startup_recovers_interrupted_runs_and_logs_it(
    config: RuntimeConfig, overrides: Overrides, caplog: pytest.LogCaptureFixture
) -> None:
    app = create_app(config, overrides)
    runtime: Runtime = app.state.runtime
    runtime.ports.runs.save(run("crashed", status=RunStatus.RUNNING))
    with caplog.at_level(logging.INFO, logger="automator"), TestClient(app) as client:
        crashed = Api(client, runtime).wait_for("crashed", "failed")
    assert "interrupted" in crashed["error"]
    assert "recovered 1 interrupted runs" in caplog.text


def test_shutdown_warns_when_workers_outlive_the_timeout(
    runtime: Runtime, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(runtime.queue, "stop", lambda _timeout: False)
    with caplog.at_level(logging.WARNING, logger="automator"):
        runtime.stop()
    assert "still working at shutdown" in caplog.text


def test_the_run_log_cap_comes_from_the_runtime_config(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    app = create_app(config.model_copy(update={"max_run_log_entries": 7}), overrides)
    runtime: Runtime = app.state.runtime
    assert runtime.ports.run_logs.max_entries == 7
    assert runtime.use_cases.runs.execute.recorder.log_policy.max_entries == 7


def test_the_doctor_policy_comes_from_the_runtime_config(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    app = create_app(config.model_copy(update={"doctor_min_free_gb": 7}), overrides)
    runtime: Runtime = app.state.runtime
    assert runtime.ports.doctor_policy.min_free_gb == 7
    assert runtime.use_cases.config.doctor.policy.min_free_gb == 7


def test_the_busy_timeout_comes_from_the_runtime_config(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    app = create_app(config.model_copy(update={"database_busy_timeout_ms": 250}), overrides)
    runtime: Runtime = app.state.runtime
    with runtime.database.engine.connect() as connection:
        assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 250
    runtime.database.dispose()
