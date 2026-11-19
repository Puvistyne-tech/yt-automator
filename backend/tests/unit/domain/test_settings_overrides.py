from __future__ import annotations

from autotube.domain.diagnostics import DoctorPolicy
from autotube.domain.run_parts import RunLogPolicy
from autotube.domain.settings import (
    AppSettings,
    AppSettingsInput,
    ServerLogLevel,
    locked_field_errors,
)
from autotube.domain.settings_overrides import (
    SettingOverride,
    doctor_policy,
    effective_settings,
    run_log_policy,
    storable_settings,
    stored_settings,
)
from tests.fixtures.retention_data import LEGACY_PAYLOAD

LOCKED_LEVEL = SettingOverride(field="log_level", value="debug", reason="Set by AUTOTUBE_X")


def test_settings_stored_before_retention_load_unchanged_with_new_defaults() -> None:
    loaded = stored_settings(LEGACY_PAYLOAD)
    assert (loaded.timezone, loaded.max_parallel_runs, loaded.keep_runs_days) == (
        "Asia/Kolkata",
        2,
        7,
    )
    assert loaded.model_dump(exclude={"timezone", "max_parallel_runs", "keep_runs_days"}) == (
        AppSettingsInput().model_dump(exclude={"timezone", "max_parallel_runs", "keep_runs_days"})
    )


def test_nothing_stored_means_every_default() -> None:
    assert stored_settings(None) == AppSettingsInput()


def test_the_default_comes_through_without_an_override() -> None:
    settings = effective_settings(AppSettingsInput(), (), "/data")
    assert settings.log_level is ServerLogLevel.INFO and settings.locked == {}
    assert settings.data_dir == "/data" and settings.restart_required == ("log_level",)


def test_a_stored_value_wins_over_the_default() -> None:
    stored = AppSettingsInput(log_level=ServerLogLevel.ERROR)
    assert effective_settings(stored, (), "/d").log_level is ServerLogLevel.ERROR


def test_an_override_wins_over_the_stored_value_and_locks_the_field() -> None:
    stored = AppSettingsInput(log_level=ServerLogLevel.ERROR)
    settings = effective_settings(stored, (LOCKED_LEVEL,), "/d")
    assert settings.log_level is ServerLogLevel.DEBUG
    assert settings.locked == {"log_level": "Set by AUTOTUBE_X"}


def test_saving_keeps_the_stored_value_of_a_locked_field() -> None:
    stored = AppSettingsInput(log_level=ServerLogLevel.ERROR)
    changes = AppSettingsInput(log_level=ServerLogLevel.DEBUG, timezone="Asia/Kolkata")
    kept = storable_settings(changes, stored, ["log_level"])
    assert kept.log_level is ServerLogLevel.ERROR and kept.timezone == "Asia/Kolkata"


def test_changing_a_locked_field_is_an_error_but_resending_it_is_not() -> None:
    current = effective_settings(AppSettingsInput(), (LOCKED_LEVEL,), "/d")
    same = current.input()
    assert locked_field_errors(same, current) == {}
    changed = same.model_copy(update={"log_level": ServerLogLevel.ERROR})
    assert locked_field_errors(changed, current) == {"log_level": "Set by AUTOTUBE_X"}


def test_input_drops_the_read_only_fields() -> None:
    settings = AppSettings(data_dir="/d", locked={"log_level": "env"})
    assert settings.input() == AppSettingsInput()


def test_run_logs_and_doctor_follow_the_settings() -> None:
    settings = AppSettingsInput(
        max_run_log_entries=9, fallback_reason_chars=40, doctor_min_free_gb=2.5
    )
    assert run_log_policy(settings) == RunLogPolicy(max_entries=9, fallback_reason_chars=40)
    base = DoctorPolicy(min_python=(3, 13))
    assert doctor_policy(base, settings) == DoctorPolicy(min_python=(3, 13), min_free_gb=2.5)
