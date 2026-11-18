from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

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
