from __future__ import annotations

from dataclasses import dataclass

from automator.domain.ports import AppSettingsRepository
from automator.domain.settings import (
    AppSettings,
    AppSettingsInput,
    app_settings_errors,
    locked_field_errors,
)
from automator.shared.errors import raise_if_invalid


@dataclass(frozen=True)
class SaveSettings:
    settings: AppSettingsRepository

    def execute(self, changes: AppSettingsInput) -> AppSettings:
        current = self.settings.get()
        raise_if_invalid(app_settings_errors(changes) | locked_field_errors(changes, current))
        self.settings.save(current.with_input(changes))
        return self.settings.get()
