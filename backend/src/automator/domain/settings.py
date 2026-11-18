from __future__ import annotations

from pydantic import Field

from automator.domain.model_base import DomainModel
from automator.shared.clock import is_valid_timezone


class AppSettingsInput(DomainModel):
    timezone: str = "UTC"
    max_parallel_runs: int = Field(default=1, ge=1)
    keep_runs_days: int = Field(default=30, ge=1)


class AppSettings(AppSettingsInput):
    data_dir: str = ""

    def with_input(self, changes: AppSettingsInput) -> AppSettings:
        return self.model_copy(update=changes.model_dump())


def app_settings_errors(settings: AppSettingsInput) -> dict[str, str]:
    if not is_valid_timezone(settings.timezone):
        return {"timezone": f"unknown timezone {settings.timezone!r}"}
    return {}
