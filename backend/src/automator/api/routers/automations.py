from __future__ import annotations

from fastapi import APIRouter, Response, status

from automator.api.container import App
from automator.api.schemas.requests import EnabledRequest
from automator.api.schemas.responses import ERROR_RESPONSES
from automator.domain.automations import Automation, AutomationInput
from automator.domain.runs import Run

router = APIRouter(prefix="/automations", tags=["automations"], responses=ERROR_RESPONSES)
CREATED = status.HTTP_201_CREATED


@router.get("", summary="List automations with next and last run")
def list_automations(app: App) -> list[Automation]:
    return app.automations.list_automations.execute()


@router.post("", status_code=CREATED, summary="Create an automation")
def create_automation(body: AutomationInput, app: App) -> Automation:
    return app.automations.create.execute(body)


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
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
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
