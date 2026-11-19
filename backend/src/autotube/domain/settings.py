from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from pydantic import Field

from autotube.domain.diagnostics import DEFAULT_MIN_FREE_GB
from autotube.domain.model_base import DomainModel
from autotube.domain.run_parts import (
    DEFAULT_FALLBACK_REASON_CHARS,
    DEFAULT_MAX_RUN_LOGS,
    MIN_FALLBACK_REASON_CHARS,
)
from autotube.domain.validation import timezone_errors


class ServerLogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AppSettingsInput(DomainModel):
    timezone: str = Field(
        default="UTC",
        title="Timezone",
        description="Used for dates in the app and as the default for new schedules",
    )
    max_parallel_runs: int = Field(
        default=1, ge=1, title="Parallel runs", description="Runs that may render at once"
    )
    keep_runs_days: int = Field(
        default=30,
        ge=0,
        title="Keep finished runs (days)",
        description="Finished runs and their folders are deleted this many days after they "
        "finish; 0 keeps them forever",
    )
    keep_intermediate_days: int = Field(
        default=0,
        ge=0,
        title="Keep working files (days)",
        description="Working files that are not final outputs are removed this many days "
        "after a run finishes; 0 keeps them",
    )
    auto_cleanup_enabled: bool = Field(
        default=False,
        title="Clean up automatically",
        description="When on, the cleanup runs on its own every interval and deletes what the "
        "retention settings allow; when off, nothing is deleted until you choose Clean up now",
    )
    cleanup_interval_hours: int = Field(
        default=24,
        ge=0,
        title="Automatic cleanup every (hours)",
        description="How often the cleanup runs on its own; 0 runs it only on demand",
    )
    caption_track_name: str = Field(
        default="",
        title="Caption track name",
        description="Name YouTube shows for uploaded caption tracks; empty leaves it unnamed",
    )
    max_run_log_entries: int = Field(
        default=DEFAULT_MAX_RUN_LOGS,
        ge=1,
        title="Log entries kept per run",
        description="Older entries are dropped once a run has this many",
    )
    fallback_reason_chars: int = Field(
        default=DEFAULT_FALLBACK_REASON_CHARS,
        ge=MIN_FALLBACK_REASON_CHARS,
        title="Fallback reason length",
        description="Characters of a failed provider's error shown when a run falls back",
    )
    log_level: ServerLogLevel = Field(
        default=ServerLogLevel.INFO,
        title="Server log level",
        description="Detail of the server log",
    )
    doctor_min_free_gb: float = Field(
        default=DEFAULT_MIN_FREE_GB,
        ge=0,
        title="Free disk space warning (GB)",
        description="The health check warns below this much free space",
    )


RESTART_REQUIRED_FIELDS: tuple[str, ...] = ("log_level",)


class AppSettings(AppSettingsInput):
    data_dir: str = ""
    locked: dict[str, str] = Field(default_factory=dict)
    restart_required: tuple[str, ...] = RESTART_REQUIRED_FIELDS

    def with_input(self, changes: AppSettingsInput) -> AppSettings:
        return self.model_copy(update=changes.model_dump())

    def input(self) -> AppSettingsInput:
        return AppSettingsInput.model_validate(self.model_dump(include=input_fields()))


def input_fields() -> set[str]:
    return set(AppSettingsInput.model_fields)


def with_sent_fields(current: AppSettingsInput, sent: Mapping[str, object]) -> AppSettingsInput:
    return AppSettingsInput.model_validate(current.model_dump() | dict(sent))


def app_settings_errors(settings: AppSettingsInput) -> dict[str, str]:
    return timezone_errors(settings.timezone)


def locked_field_errors(changes: AppSettingsInput, current: AppSettings) -> dict[str, str]:
    return {
        name: reason
        for name, reason in current.locked.items()
        if getattr(changes, name) != getattr(current, name)
    }
