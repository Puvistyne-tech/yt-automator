from __future__ import annotations

import logging
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from autotube.domain.run_enums import RunStatus
from autotube.infrastructure.config import RuntimeConfig
from autotube.main import Overrides, Runtime, create_app, youtube_gateway
from tests.fixtures.template_records import template
from tests.unit.api.client import Api
from tests.unit.infrastructure.records import run

BROKEN_ROW = (
    "INSERT INTO pipeline_templates (id, type_id, status, created_at, payload) "
    """VALUES ('old', 't_old', 'ready', '0', '{"audience": "teens"}')"""
)


def test_caption_names_follow_the_saved_settings(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    runtime: Runtime = create_app(config, overrides).state.runtime
    gateway = youtube_gateway(config, runtime.ports.app_settings)
    runtime.ports.app_settings.save(
        runtime.ports.app_settings.get().model_copy(update={"caption_track_name": "Tamil"})
    )
    assert gateway.caption_name() == "Tamil"
    runtime.database.dispose()


def test_youtube_settings_come_from_the_runtime_config() -> None:
    config = RuntimeConfig(
        youtube_caption_track_name="English",
        youtube_playlist_page_size=10,
        upload_chunk_bytes=512 * 1024,
    )
    gateway = youtube_gateway(config)
    settings = gateway.settings
    assert (settings.caption_track_name, settings.playlist_page_size) == ("English", 10)
    assert gateway.caption_name() == "English"
    assert settings.upload_chunk_bytes == 512 * 1024
    assert settings.redirect_uri == config.oauth_redirect_uri


def test_startup_recovers_interrupted_runs_and_logs_it(
    config: RuntimeConfig, overrides: Overrides, caplog: pytest.LogCaptureFixture
) -> None:
    app = create_app(config, overrides)
    runtime: Runtime = app.state.runtime
    runtime.ports.runs.save(run("crashed", status=RunStatus.RUNNING))
    with caplog.at_level(logging.INFO, logger="autotube"), TestClient(app) as client:
        crashed = Api(client, runtime).wait_for("crashed", "failed")
    assert "interrupted" in crashed["error"]
    assert "recovered 1 interrupted runs" in caplog.text


def test_shutdown_warns_when_workers_outlive_the_timeout(
    runtime: Runtime, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(runtime.queue, "stop", lambda _timeout: False)
    with caplog.at_level(logging.WARNING, logger="autotube"):
        runtime.stop()
    assert "still working at shutdown" in caplog.text


def test_the_run_log_cap_comes_from_the_runtime_config(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    app = create_app(config.model_copy(update={"max_run_log_entries": 7}), overrides)
    runtime: Runtime = app.state.runtime
    assert runtime.use_cases.runs.execute.recorder.log_policy().max_entries == 7


def test_the_doctor_policy_comes_from_the_runtime_config(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    app = create_app(config.model_copy(update={"doctor_min_free_gb": 7}), overrides)
    runtime: Runtime = app.state.runtime
    assert runtime.use_cases.config.doctor.policy().min_free_gb == 7


def test_the_busy_timeout_comes_from_the_runtime_config(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    app = create_app(config.model_copy(update={"database_busy_timeout_ms": 250}), overrides)
    runtime: Runtime = app.state.runtime
    with runtime.database.engine.connect() as connection:
        assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 250
    runtime.database.dispose()


def test_the_composed_registry_serves_stored_ready_templates(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    app = create_app(config, replace(overrides, pipelines=None))
    runtime: Runtime = app.state.runtime
    runtime.ports.templates.add(template())
    with runtime.database.engine.begin() as connection:
        connection.execute(text(BROKEN_ROW))
    listed = [pipeline.descriptor.type_id for pipeline in runtime.ports.pipelines.list()]
    assert listed == ["kids_story", "t_tpl-1"]
    runtime.database.dispose()
