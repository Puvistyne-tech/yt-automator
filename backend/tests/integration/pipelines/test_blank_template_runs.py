from __future__ import annotations

from collections.abc import Callable

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.run_enums import ArtifactKind, RunStatus, StageStatus
from autotube.domain.runs import Run
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.publishing.audience_check import metadata_texts
from autotube.pipelines.narrated_video.publishing.metadata import UploadMetadata
from autotube.pipelines.narrated_video.story.child_terms import child_terms_in_any
from autotube.pipelines.narrated_video.template.merging import deep_merged
from tests.fixtures.explainer_data import TAKEAWAY_EN, explainer_writer
from tests.fixtures.harness import Harness
from tests.fixtures.kids_data import smart_writer
from tests.fixtures.kids_fakes import FakeWriter
from tests.fixtures.pipeline_runs import PAIRS, executed_run, pairs, planned_uploads
from tests.fixtures.quick_sections import QUICK_SECTIONS
from tests.fixtures.template_records import template
from tests.fixtures.template_settings import GENERAL, KIDS, general_writer

pytestmark = pytest.mark.integration


def blank_run(
    harness: Harness, audience: TemplateAudience, structure: str, writer: FakeWriter
) -> Run:
    engine = NarratedVideoEngine()
    definition = {**engine.blank(audience), "structure": structure}
    pipeline = engine.pipeline(template(audience=audience, definition=definition))
    settings = deep_merged(pipeline.descriptor.default_settings, QUICK_SECTIONS)
    type_id = pipeline.descriptor.type_id
    return executed_run(harness, [pipeline], type_id, settings, writer)


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
    kids = audience is KIDS
    assert found and all(item.made_for_kids is kids for item in found)
    assert all("{" not in item.title + item.description for item in found)
    if not kids:
        assert all(child_terms_in_any(metadata_texts(item)) == [] for item in found)
    plans = planned_uploads(harness, run)
    assert plans and all(plan.made_for_kids is kids for plan in plans)


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_a_blank_explainer_runs_offline_for_each_audience(
    harness: Harness, audience: TemplateAudience
) -> None:
    run = blank_run(harness, audience, "explainer", explainer_writer())
    assert_published_offline(run, harness, audience)
    english = [item for item in upload_details(run) if item.default_language == "en"]
    assert any(TAKEAWAY_EN in item.description for item in english)


@pytest.mark.parametrize(("audience", "writer"), [(KIDS, smart_writer), (GENERAL, general_writer)])
def test_a_blank_story_runs_offline_for_each_audience(
    harness: Harness, audience: TemplateAudience, writer: Callable[[], FakeWriter]
) -> None:
    run = blank_run(harness, audience, "story", writer())
    assert_published_offline(run, harness, audience)
