from __future__ import annotations

from fastapi import APIRouter

from autotube.api.container import App
from autotube.api.schemas.requests import EnabledRequest, ImportRequest
from autotube.api.schemas.responses import CREATED, ERROR_RESPONSES, NO_CONTENT_RESPONSE
from autotube.domain.automation_export import AutomationDocument, ImportPreview
from autotube.domain.automations import Automation, AutomationInput
from autotube.domain.runs import Run

router = APIRouter(prefix="/automations", tags=["automations"], responses=ERROR_RESPONSES)


@router.get("", summary="List automations with next and last run")
def list_automations(app: App) -> list[Automation]:
    return app.automations.list_automations.execute()


@router.post("", status_code=CREATED, summary="Create an automation")
def create_automation(body: AutomationInput, app: App) -> Automation:
    return app.automations.create.execute(body)


@router.post(
    "/import/preview",
    summary="Check an automation export and list the channels that need a choice",
)
def preview_import(body: ImportRequest, app: App) -> ImportPreview:
    return app.automations.import_automation.preview(body.document, body.channel_map)


@router.post(
    "/import",
    status_code=CREATED,
    summary="Create a disabled automation from an export",
)
def import_automation(body: ImportRequest, app: App) -> Automation:
    return app.automations.import_automation.execute(body.document, body.channel_map)


@router.get("/{automation_id}/export", summary="Export an automation as a portable document")
def export_automation(automation_id: str, app: App) -> AutomationDocument:
    return app.automations.export.execute(automation_id)


@router.get("/{automation_id}", summary="Get one automation")
def get_automation(automation_id: str, app: App) -> Automation:
    return app.automations.get.execute(automation_id)


@router.put("/{automation_id}", summary="Replace an automation's definition")
def update_automation(automation_id: str, body: AutomationInput, app: App) -> Automation:
    return app.automations.update.execute(automation_id, body)


@router.patch("/{automation_id}", summary="Enable or disable an automation")
def set_enabled(automation_id: str, body: EnabledRequest, app: App) -> Automation:
    return app.automations.set_enabled.execute(automation_id, body.enabled)


@router.delete(
    "/{automation_id}",
    **NO_CONTENT_RESPONSE,
    summary="Delete an automation and keep its runs",
)
def delete_automation(automation_id: str, app: App) -> None:
    app.automations.delete.execute(automation_id)


@router.post("/{automation_id}/duplicate", status_code=CREATED, summary="Copy an automation")
def duplicate_automation(automation_id: str, app: App) -> Automation:
    return app.automations.duplicate.execute(automation_id)


@router.post("/{automation_id}/runs", status_code=CREATED, summary="Start a run now")
def start_run(automation_id: str, app: App) -> Run:
    return app.automations.start_run.execute(automation_id)
