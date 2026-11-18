from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from automator.application.clean_up_storage import CleanUpStorage
from automator.domain.ports import AppSettingsRepository
from automator.domain.retention import CleanupReport, cleanup_due


@dataclass
class ScheduledCleanup:
    cleanup: CleanUpStorage
    settings: AppSettingsRepository
    last_ran: datetime | None = None

    def execute(self, now: datetime) -> CleanupReport | None:
        if not cleanup_due(self.last_ran, now, self.settings.get().cleanup_interval_hours):
            return None
        self.last_ran = now
        return self.cleanup.execute()
