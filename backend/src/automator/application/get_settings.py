from __future__ import annotations

from dataclasses import dataclass

from automator.domain.ports import AppSettingsRepository
from automator.domain.settings import AppSettings


@dataclass(frozen=True)
class GetSettings:
    settings: AppSettingsRepository

    def execute(self) -> AppSettings:
        return self.settings.get()
