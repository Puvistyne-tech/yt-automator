from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from autotube.application.clean_up_storage import CleanUpStorage
from autotube.domain.ports import AppSettingsRepository
from autotube.domain.retention import CleanupReport, cleanup_due


@dataclass
class ScheduledCleanup:
    cleanup: CleanUpStorage
    settings: AppSettingsRepository
    last_ran: datetime | None = None

    def execute(self, now: datetime) -> CleanupReport | None:
        if not cleanup_due(self.last_ran, now, self.settings.get()):
            return None
        self.last_ran = now
        return self.cleanup.execute()
