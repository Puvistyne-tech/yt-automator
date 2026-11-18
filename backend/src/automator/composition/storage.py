from __future__ import annotations

from automator.api.container import StorageUseCases
from automator.application.clean_up_storage import CleanUpStorage
from automator.application.cleanup_planner import CleanupPlanner
from automator.application.get_storage import GetStorage
from automator.application.preview_cleanup import PreviewCleanup
from automator.application.scheduled_cleanup import ScheduledCleanup
from automator.composition.ports import Collaborators, Ports


def storage_use_cases(p: Ports, c: Collaborators) -> StorageUseCases:
    planner = CleanupPlanner(p.runs, p.files, p.app_settings, p.clock)
    clean_up = CleanUpStorage(planner, p.runs, p.files, c.recorder)
    return StorageUseCases(
        get_storage=GetStorage(planner, p.files),
        preview_cleanup=PreviewCleanup(planner),
        clean_up=clean_up,
        scheduled_cleanup=ScheduledCleanup(clean_up, p.app_settings),
    )
