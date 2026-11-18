from __future__ import annotations

from autotube.api.container import StorageUseCases
from autotube.application.clean_up_storage import CleanUpStorage
from autotube.application.cleanup_planner import CleanupPlanner
from autotube.application.get_storage import GetStorage
from autotube.application.preview_cleanup import PreviewCleanup
from autotube.application.scheduled_cleanup import ScheduledCleanup
from autotube.composition.ports import Collaborators, Ports


def storage_use_cases(p: Ports, c: Collaborators) -> StorageUseCases:
    planner = CleanupPlanner(p.runs, p.files, p.app_settings, p.clock, p.automations)
    clean_up = CleanUpStorage(planner, p.runs, p.files, c.recorder)
    return StorageUseCases(
        get_storage=GetStorage(planner, p.files),
        preview_cleanup=PreviewCleanup(planner),
        clean_up=clean_up,
        scheduled_cleanup=ScheduledCleanup(clean_up, p.app_settings),
    )
