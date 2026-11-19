from __future__ import annotations

import logging
from typing import Any

import pytest

from autotube.domain.settings import ServerLogLevel
from autotube.infrastructure.config import RuntimeConfig
from autotube.main import Overrides
from tests.unit.api.client import Api, error_of, ok, wired

DEFAULT_SETTINGS: dict[str, Any] = {
    "timezone": "UTC",
    "max_parallel_runs": 1,
    "keep_runs_days": 30,
    "keep_intermediate_days": 0,
    "auto_cleanup_enabled": False,
    "cleanup_interval_hours": 24,
    "caption_track_name": "",
    "max_run_log_entries": 2000,
    "fallback_reason_chars": 200,
    "log_level": "info",
    "doctor_min_free_gb": 10.0,
    "locked": {},
    "restart_required": ["log_level"],
}


def test_settings_round_trip_with_read_only_fields(api: Api) -> None:
    client = api.client
    data_dir = str(api.runtime.config.data_dir)
    current = ok(client.get("/api/settings"))
    assert current == DEFAULT_SETTINGS | {"data_dir": data_dir}
    changes = {"timezone": "Asia/Kolkata", "keep_runs_days": 0, "caption_track_name": "English"}
    sent = current | changes | {"data_dir": "/x", "locked": {"timezone": "no"}}
    saved = ok(client.put("/api/settings", json=sent))
    assert saved == current | changes
    assert ok(client.get("/api/settings")) == saved


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"timezone": "Mars/Base"}, "timezone"),
        ({"max_parallel_runs": 0}, "max_parallel_runs"),
        ({"keep_runs_days": -1}, "keep_runs_days"),
        ({"keep_intermediate_days": -1}, "keep_intermediate_days"),
        ({"cleanup_interval_hours": 1.5}, "cleanup_interval_hours"),
        ({"max_run_log_entries": 0}, "max_run_log_entries"),
        ({"fallback_reason_chars": 19}, "fallback_reason_chars"),
        ({"log_level": "loud"}, "log_level"),
        ({"doctor_min_free_gb": -0.5}, "doctor_min_free_gb"),
    ],
)
def test_invalid_settings_name_the_field(api: Api, body: dict[str, Any], field: str) -> None:
    assert field in error_of(api.client.put("/api/settings", json=body), 400)["fields"]


def locked_app(config: RuntimeConfig, overrides: Overrides) -> Any:
    env_config = config.model_copy(
        update={"log_level": ServerLogLevel.DEBUG, "max_run_log_entries": 7}
    )
    return wired(env_config, overrides)


def test_environment_values_win_and_lock_their_fields(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    with locked_app(config, overrides) as client:
        current = ok(client.get("/api/settings"))
        assert (current["log_level"], current["max_run_log_entries"]) == ("debug", 7)
        assert set(current["locked"]) == {"log_level", "max_run_log_entries"}
        assert "AUTOTUBE_LOG_LEVEL" in current["locked"]["log_level"]
        saved = ok(client.put("/api/settings", json=current | {"timezone": "Asia/Kolkata"}))
        assert saved["timezone"] == "Asia/Kolkata" and saved["max_run_log_entries"] == 7
        refused = error_of(client.put("/api/settings", json=current | {"log_level": "error"}), 400)
        assert set(refused["fields"]) == {"log_level"}


def test_a_partial_save_changes_only_the_sent_fields(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    with locked_app(config, overrides) as client:
        ok(client.put("/api/settings", json={"keep_runs_days": 9, "timezone": "Asia/Kolkata"}))
        saved = ok(client.put("/api/settings", json={"auto_cleanup_enabled": True}))
    assert (saved["keep_runs_days"], saved["timezone"]) == (9, "Asia/Kolkata")
    assert saved["auto_cleanup_enabled"] and saved["max_run_log_entries"] == 7


def test_a_locked_field_keeps_its_stored_value_underneath(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    with wired(config, overrides) as client:
        ok(client.put("/api/settings", json={"max_run_log_entries": 50}))
    with locked_app(config, overrides) as client:
        locked = ok(client.get("/api/settings"))
        ok(client.put("/api/settings", json=locked | {"timezone": "Asia/Kolkata"}))
    with wired(config, overrides) as client:
        assert ok(client.get("/api/settings"))["max_run_log_entries"] == 50


def test_run_logs_follow_the_saved_cap_without_a_restart(api: Api) -> None:
    ok(api.client.put("/api/settings", json={"max_run_log_entries": 3}))
    recorder = api.runtime.use_cases.runs.execute.recorder
    assert recorder.log_policy().max_entries == 3


def test_the_doctor_follows_the_saved_free_space_threshold(api: Api) -> None:
    ok(api.client.put("/api/settings", json={"doctor_min_free_gb": 100}))
    disk = next(c for c in ok(api.client.get("/api/doctor"))["checks"] if c["name"] == "disk_space")
    assert disk["status"] == "warning" and "100 GB" in disk["detail"]


def test_the_server_log_level_is_applied_at_the_next_start(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    logger = logging.getLogger("autotube")
    try:
        with wired(config, overrides) as client:
            ok(client.put("/api/settings", json={"log_level": "warning"}))
            assert logger.level == logging.INFO
        with wired(config, overrides):
            assert logger.level == logging.WARNING
    finally:
        logger.setLevel(logging.NOTSET)
