from __future__ import annotations

from automator.domain.run_enums import RunStatus
from automator.domain.settings import AppSettings, ServerLogLevel
from automator.domain.settings_overrides import SettingOverride
from automator.infrastructure.config import RuntimeConfig
from automator.infrastructure.db.database import Database
from automator.infrastructure.db.run_repository import SqlRunRepository
from automator.infrastructure.db.settings_repositories import (
    APP_SETTINGS_ID,
    SqlAppSettingsRepository,
)
from automator.infrastructure.db.tables import AppSettingsRow
from automator.infrastructure.settings_env import settings_overrides
from tests.unit.infrastructure.records import run

LEGACY_PAYLOAD = {
    "timezone": "Asia/Kolkata",
    "max_parallel_runs": 2,
    "keep_runs_days": 7,
    "data_dir": "",
}
LOCKED = SettingOverride(field="log_level", value="debug", reason="Set by env")


def test_settings_saved_before_this_change_load_unchanged(database: Database) -> None:
    with database.session() as session:
        session.add(AppSettingsRow(id=APP_SETTINGS_ID, payload=LEGACY_PAYLOAD))
    loaded = SqlAppSettingsRepository(database, "/data").get()
    assert loaded == AppSettings(
        timezone="Asia/Kolkata", max_parallel_runs=2, keep_runs_days=7, data_dir="/data"
    )


def test_the_environment_wins_and_the_stored_value_survives_a_save(database: Database) -> None:
    plain = SqlAppSettingsRepository(database, "/data")
    plain.save(plain.get().model_copy(update={"log_level": ServerLogLevel.ERROR}))
    locked = SqlAppSettingsRepository(database, "/data", (LOCKED,))
    current = locked.get()
    assert current.log_level is ServerLogLevel.DEBUG and current.locked == {
        "log_level": "Set by env"
    }
    locked.save(current.model_copy(update={"timezone": "Asia/Kolkata"}))
    with database.session() as session:
        row = session.get(AppSettingsRow, APP_SETTINGS_ID)
        assert row is not None and row.payload["log_level"] == "error"
        assert "locked" not in row.payload and "data_dir" not in row.payload
    assert plain.get().log_level is ServerLogLevel.ERROR
    assert plain.get().timezone == "Asia/Kolkata"


def test_delete_if_removes_only_a_run_that_passes_the_check(database: Database) -> None:
    runs = SqlRunRepository(database)
    runs.save(run("r1", status=RunStatus.PUBLISHED))
    assert runs.delete_if("r1", lambda stored: stored.status is RunStatus.QUEUED) is None
    assert runs.get("r1") is not None
    deleted = runs.delete_if("r1", lambda stored: stored.status is RunStatus.PUBLISHED)
    assert deleted is not None and deleted.id == "r1" and runs.get("r1") is None
    assert runs.delete_if("r1", lambda _stored: True) is None


def test_only_environment_variables_that_are_set_become_overrides() -> None:
    assert settings_overrides(RuntimeConfig()) == ()
    config = RuntimeConfig.model_validate(
        {"youtube_caption_track_name": "English", "cleanup_interval_hours": 0, "port": 9000}
    )
    overrides = settings_overrides(config)
    assert {(o.field, o.value) for o in overrides} == {
        ("caption_track_name", "English"),
        ("cleanup_interval_hours", 0),
    }
    reasons = {o.field: o.reason for o in overrides}
    assert "AUTOMATOR_YOUTUBE_CAPTION_TRACK_NAME" in reasons["caption_track_name"]


def test_an_environment_log_level_is_stored_as_its_name() -> None:
    config = RuntimeConfig.model_validate({"log_level": "warning"})
    assert [(o.field, o.value) for o in settings_overrides(config)] == [("log_level", "warning")]
