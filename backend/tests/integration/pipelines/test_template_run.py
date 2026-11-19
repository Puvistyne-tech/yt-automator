from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.artifact_selection import text_list
from autotube.domain.pipeline import Pipeline
from autotube.domain.run_enums import ArtifactKind, RunStatus, StageStatus
from autotube.domain.run_parts import Artifact
from autotube.domain.runs import Run
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.publishing.audience_check import metadata_texts
from autotube.pipelines.narrated_video.publishing.metadata import UploadMetadata
from autotube.pipelines.narrated_video.story.child_terms import child_terms_in_any
from autotube.pipelines.narrated_video.template.merging import deep_merged
from tests.fixtures.harness import Harness
from tests.fixtures.kids_data import smart_writer
from tests.fixtures.kids_fakes import FakeWriter, failing_writer
from tests.fixtures.pipeline_runs import PAIRS, executed_run, pairs, planned_uploads
from tests.fixtures.quick_sections import QUICK_SECTIONS
from tests.fixtures.template_settings import GENERAL, general_writer, pipeline_of

pytestmark = pytest.mark.integration
GENERAL_DEFINITION: dict[str, Any] = {
    "brief": "Quiet tales about everyday courage.",
    "tone": "calm, wry",
    "title_template": {"en": "{title} | Quiet Tales"},
    "description_template": {"en": "{title}: a quiet tale about {theme}."},
    "tags": {"en": ["calm stories"]},
}
GENERAL_LINE = "The audience is general: the script must never address children"


def run_of(harness: Harness, pipeline: Pipeline, writer: FakeWriter, **changes: Any) -> Run:
    base = deep_merged(pipeline.descriptor.default_settings, QUICK_SECTIONS)
    settings = deep_merged(base, changes)
    type_id = pipeline.descriptor.type_id
    return executed_run(harness, [pipeline], type_id, settings, writer)


def general_run(harness: Harness, writer: FakeWriter, **changes: Any) -> Run:
    return run_of(harness, pipeline_of(GENERAL, **GENERAL_DEFINITION), writer, **changes)


def assert_complete(run: Run) -> None:
    assert run.status is RunStatus.AWAITING_REVIEW, run.error
    assert all(stage.status is StageStatus.DONE for stage in run.stages)
    assert run.score is not None and run.score > 80
    assert pairs(run, ArtifactKind.METADATA) == PAIRS


def uploads(run: Run) -> list[Artifact]:
    return [item for item in run.artifacts if item.meta.get("role") == "upload_metadata"]


def details(item: Artifact) -> UploadMetadata:
    fields = set(UploadMetadata.model_fields)
    return UploadMetadata.model_validate({k: v for k, v in item.meta.items() if k in fields})


def test_a_general_story_template_runs_offline_and_is_not_made_for_kids(harness: Harness) -> None:
    writer = general_writer()
    run = general_run(harness, writer)
    assert_complete(run)
    system = writer.requests[0].system or ""
    assert GENERAL_LINE in system and "children aged" not in system
    found = [details(item) for item in uploads(run)]
    assert found and all(item.made_for_kids is False for item in found)
    assert all(child_terms_in_any(metadata_texts(item)) == [] for item in found)
    episode = next(
        item for item in found if item.default_language == "en" and "#" not in item.title
    )
    assert episode.title.endswith("| Quiet Tales") and "a quiet tale about" in episode.description
    assert all(
        text_list(item.tags) == ("calm stories",) for item in found if item.default_language == "en"
    )
    stage = run.stage("story")
    assert stage is not None and stage.provider != "bundled"
    plans = planned_uploads(harness, run)
    assert plans and not any(plan.made_for_kids for plan in plans)


def test_a_general_run_fails_instead_of_using_a_bundled_story(harness: Harness) -> None:
    run = general_run(harness, failing_writer())
    assert run.status is RunStatus.FAILED
    assert "never falls back" in (run.error or "")
    assert pairs(run, ArtifactKind.METADATA) == set()


@pytest.mark.parametrize(
    ("changes", "failed_stage"),
    [
        ({"metadata": {"tags": {"en": ["kids stories"]}}}, "package"),
        ({"series": {"intro_line": {"en": "Hello, little friends!"}}}, "story"),
    ],
)
def test_child_directed_automation_edits_fail_the_general_run_before_upload(
    harness: Harness, changes: dict[str, Any], failed_stage: str
) -> None:
    run = general_run(harness, general_writer(), **changes)
    assert run.status is RunStatus.FAILED
    stage = run.stage(failed_stage)
    assert stage is not None and stage.status is StageStatus.FAILED
    assert pairs(run, ArtifactKind.METADATA) == set()


def test_the_kids_builtin_runs_offline_through_the_engine(harness: Harness) -> None:
    engine = NarratedVideoEngine()
    pipeline = engine.pipeline(engine.builtin_templates()[0])
    run = run_of(harness, pipeline, smart_writer())
    assert_complete(run)
    found = [details(item) for item in uploads(run)]
    assert found and all(item.made_for_kids is True for item in found)
    engine_tags = pipeline.descriptor.default_settings["metadata"]
    assert isinstance(engine_tags, dict) and isinstance(engine_tags["tags"], dict)
    assert all(list(item.tags) == engine_tags["tags"][item.default_language] for item in found)
    plans = planned_uploads(harness, run)
    assert plans and all(plan.made_for_kids for plan in plans)
