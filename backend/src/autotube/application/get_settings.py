from __future__ import annotations

from dataclasses import dataclass

from autotube.domain.ports import AppSettingsRepository
from autotube.domain.settings import AppSettings


@dataclass(frozen=True)
class GetSettings:
    settings: AppSettingsRepository

    def execute(self) -> AppSettings:
        return self.settings.get()
