from __future__ import annotations

from dataclasses import dataclass

from automator.domain.ports import AppSettingsRepository
from automator.domain.settings import AppSettings, AppSettingsInput, app_settings_errors
from automator.shared.errors import ValidationFailed


@dataclass(frozen=True)
class SaveSettings:
    settings: AppSettingsRepository

    def execute(self, changes: AppSettingsInput) -> AppSettings:
        errors = app_settings_errors(changes)
        if errors:
            raise ValidationFailed(errors)
        updated = self.settings.get().with_input(changes)
        self.settings.save(updated)
        return updated
