from __future__ import annotations

from dataclasses import dataclass

from automator.domain.ports import AppSettingsRepository
from automator.domain.settings import AppSettings, AppSettingsInput, app_settings_errors
from automator.shared.errors import raise_if_invalid


@dataclass(frozen=True)
class SaveSettings:
    settings: AppSettingsRepository

    def execute(self, changes: AppSettingsInput) -> AppSettings:
        raise_if_invalid(app_settings_errors(changes))
        updated = self.settings.get().with_input(changes)
        self.settings.save(updated)
        return updated
