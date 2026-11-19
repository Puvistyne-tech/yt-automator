from __future__ import annotations

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.run_enums import ArtifactKind, RunStatus, StageStatus
from autotube.domain.runs import Run
from autotube.pipelines.narrated_video.publishing.audience_check import (
    checked_audience,
    metadata_texts,
)
from autotube.pipelines.narrated_video.publishing.metadata import UploadMetadata
from autotube.pipelines.narrated_video.story.child_terms import child_terms_in_any
from tests.fixtures.harness import Harness
from tests.fixtures.pipeline_runs import PAIRS, pairs, planned_uploads


def upload_details(run: Run) -> list[UploadMetadata]:
    fields = set(UploadMetadata.model_fields)
    return [
        UploadMetadata.model_validate({k: v for k, v in item.meta.items() if k in fields})
        for item in run.artifacts
        if item.meta.get("role") == "upload_metadata"
    ]


def assert_published_offline(run: Run, harness: Harness, audience: TemplateAudience) -> None:
    assert run.status is RunStatus.AWAITING_REVIEW, run.error
    assert all(stage.status is StageStatus.DONE for stage in run.stages)
    assert run.score is not None and run.score > 80
    assert pairs(run, ArtifactKind.METADATA) == PAIRS
    story = run.stage("story")
    assert story is not None and story.provider != "bundled"
    found = upload_details(run)
    kids = audience is TemplateAudience.KIDS
    assert found and all(item.made_for_kids is kids for item in found)
    assert all(checked_audience(item) == item for item in found)
    assert all("{" not in item.title + item.description for item in found)
    if not kids:
        assert all(child_terms_in_any(metadata_texts(item)) == [] for item in found)
    plans = planned_uploads(harness, run)
    assert plans and all(plan.made_for_kids is kids for plan in plans)
