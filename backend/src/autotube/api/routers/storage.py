from __future__ import annotations

from fastapi import APIRouter

from autotube.api.container import App
from autotube.api.schemas.responses import ERROR_RESPONSES
from autotube.domain.retention import CleanupReport
from autotube.domain.storage import StorageReport

router = APIRouter(tags=["storage"], responses=ERROR_RESPONSES)


@router.get("/storage", summary="Disk use of the data folder, per automation and kind of file")
def get_storage(app: App) -> StorageReport:
    return app.storage.get_storage.execute()


@router.get("/storage/cleanup", summary="Preview what a cleanup would remove, removing nothing")
def preview_cleanup(app: App) -> CleanupReport:
    return app.storage.preview_cleanup.execute()


@router.post("/storage/cleanup", summary="Remove expired runs, working files and stray folders")
def clean_up(app: App) -> CleanupReport:
    return app.storage.clean_up.execute()
