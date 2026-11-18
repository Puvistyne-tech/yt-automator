from __future__ import annotations

from fastapi import APIRouter

from automator.api.container import App, Options
from automator.api.schemas.responses import ERROR_RESPONSES, HealthResponse
from automator.domain.dashboard import DashboardSummary
from automator.domain.diagnostics import DoctorReport
from automator.domain.pipeline_descriptors import PipelineDescriptor

router = APIRouter(tags=["system"], responses=ERROR_RESPONSES)


@router.get("/health", summary="Report that the API is up")
def health(options: Options) -> HealthResponse:
    return HealthResponse(status="ok", version=options.version)


@router.get("/dashboard", summary="Counts, recent runs and quota usage")
def dashboard(app: App) -> DashboardSummary:
    return app.config.get_dashboard.execute()


@router.get("/pipelines", summary="List installed pipeline types")
def list_pipelines(app: App) -> list[PipelineDescriptor]:
    return app.config.list_pipelines.execute()


@router.get("/pipelines/{type_id}", summary="Describe one pipeline type")
def get_pipeline(type_id: str, app: App) -> PipelineDescriptor:
    return app.config.get_pipeline.execute(type_id)


@router.get("/doctor", summary="Check providers, secrets, tools, database and the UI build")
def doctor(app: App) -> DoctorReport:
    return app.config.doctor.execute()
