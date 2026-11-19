from __future__ import annotations

from fastapi import APIRouter

from autotube.api.container import App
from autotube.api.schemas.requests import DuplicateTemplateRequest
from autotube.api.schemas.responses import CREATED, ERROR_RESPONSES, NO_CONTENT_RESPONSE
from autotube.domain.sample_scripts import SampleScript, TemplatePreviewInput
from autotube.domain.template_inputs import TemplateInput
from autotube.domain.template_suggestions import SuggestionRequest, TemplateSuggestions
from autotube.domain.template_views import EngineSummary, TemplateSummary

router = APIRouter(tags=["templates"], responses=ERROR_RESPONSES)


@router.get("/template-engines", summary="Installed template engines and their definition forms")
def list_engines(app: App) -> list[EngineSummary]:
    return app.templates.list_engines.execute()


@router.get("/templates", summary="Built-in and saved pipeline templates")
def list_templates(app: App) -> list[TemplateSummary]:
    return app.templates.list_templates.execute()


@router.post("/templates", status_code=CREATED, summary="Create a pipeline template")
def create_template(body: TemplateInput, app: App) -> TemplateSummary:
    return app.templates.create.execute(body)


@router.post(
    "/templates/preview-script",
    summary="Write a sample script for an unsaved template without storing anything",
)
def preview_script(body: TemplatePreviewInput, app: App) -> SampleScript:
    return app.templates.preview.execute(body)


@router.post(
    "/templates/suggestions",
    summary="Suggest draft templates from what is trending without storing anything",
)
def suggest_templates(body: SuggestionRequest, app: App) -> TemplateSuggestions:
    return app.templates.suggest.execute(body)


@router.get("/templates/{template_id}", summary="Get one pipeline template")
def get_template(template_id: str, app: App) -> TemplateSummary:
    return app.templates.get.execute(template_id)


@router.put("/templates/{template_id}", summary="Replace a saved template's editable fields")
def update_template(template_id: str, body: TemplateInput, app: App) -> TemplateSummary:
    return app.templates.update.execute(template_id, body)


@router.delete(
    "/templates/{template_id}",
    **NO_CONTENT_RESPONSE,
    summary="Delete a saved template no automation uses",
)
def delete_template(template_id: str, app: App) -> None:
    app.templates.delete.execute(template_id)


@router.post(
    "/templates/{template_id}/duplicate",
    status_code=CREATED,
    summary="Copy a template as a new draft",
)
def duplicate_template(
    template_id: str, app: App, body: DuplicateTemplateRequest | None = None
) -> TemplateSummary:
    chosen = body or DuplicateTemplateRequest()
    return app.templates.duplicate.execute(template_id, chosen.name, chosen.audience)
