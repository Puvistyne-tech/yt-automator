from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from autotube.domain.ports import AppSettingsRepository
from autotube.domain.settings import (
    AppSettings,
    app_settings_errors,
    locked_field_errors,
    with_sent_fields,
)
from autotube.shared.errors import raise_if_invalid


@dataclass(frozen=True)
class SaveSettings:
    settings: AppSettingsRepository

    def execute(self, sent: Mapping[str, object]) -> AppSettings:
        current = self.settings.get()
        changes = with_sent_fields(current.input(), sent)
        raise_if_invalid(app_settings_errors(changes) | locked_field_errors(changes, current))
        self.settings.save(current.with_input(changes))
        return self.settings.get()
