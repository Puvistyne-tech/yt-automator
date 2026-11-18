from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from automator.api.container import App, Options
from automator.api.schemas.requests import RetryRequest, ReviewRequest
from automator.api.schemas.responses import ERROR_RESPONSES, NO_CONTENT_RESPONSE
from automator.domain.run_enums import RunStatus
from automator.domain.runs import Run, RunQuery
from automator.shared.errors import ValidationFailed

router = APIRouter(prefix="/runs", tags=["runs"], responses=ERROR_RESPONSES)


@router.get("", summary="List runs, newest first")
def list_runs(
    app: App,
    options: Options,
    automation_id: str | None = None,
    run_status: Annotated[RunStatus | None, Query(alias="status")] = None,
    limit: Annotated[int | None, Query(ge=1)] = None,
) -> list[Run]:
    if limit is not None and limit > options.max_run_list_limit:
        raise ValidationFailed({"limit": f"must be at most {options.max_run_list_limit}"})
    query = RunQuery(automation_id=automation_id, status=run_status, limit=limit)
    return app.runs.list_runs.execute(query)


@router.get("/{run_id}", summary="Get one run")
def get_run(run_id: str, app: App) -> Run:
    return app.runs.get.execute(run_id)


@router.post("/{run_id}/retry", summary="Queue the run again from a stage")
def retry_run(run_id: str, app: App, body: RetryRequest | None = None) -> Run:
    return app.runs.retry.execute(run_id, body.from_stage if body is not None else None)


@router.post("/{run_id}/cancel", summary="Cancel a run")
def cancel_run(run_id: str, app: App) -> Run:
    return app.runs.cancel.execute(run_id)


@router.post("/{run_id}/review", summary="Approve or reject a run awaiting review")
def review_run(run_id: str, body: ReviewRequest, app: App) -> Run:
    return app.runs.review.execute(run_id, body.decision, body.notes)


@router.post("/{run_id}/publish", summary="Upload an approved run to its targets")
def publish_run(run_id: str, app: App) -> Run:
    return app.runs.publish.execute(run_id)


@router.delete(
    "/{run_id}",
    **NO_CONTENT_RESPONSE,
    summary="Delete a finished run and its files",
)
def delete_run(run_id: str, app: App) -> None:
    app.runs.delete.execute(run_id)


@router.get(
    "/{run_id}/artifacts/{artifact_id}",
    response_class=FileResponse,
    summary="Download an artifact, with HTTP range support",
)
def get_artifact(run_id: str, artifact_id: str, app: App) -> FileResponse:
    artifact, path = app.runs.open_artifact.execute(run_id, artifact_id)
    return FileResponse(
        path,
        media_type=artifact.media_type,
        filename=PurePosixPath(artifact.filename).name,
        content_disposition_type="inline",
    )
