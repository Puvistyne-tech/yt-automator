from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.artifact_selection import text_list
from autotube.domain.pipeline import Pipeline
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.run_enums import ArtifactKind, RunStatus, StageStatus
from autotube.domain.runs import Run
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.template.merging import deep_merged
from tests.fixtures.harness import Harness
from tests.fixtures.kids_data import smart_writer
from tests.fixtures.pipeline_runs import PAIRS, executed_run, pairs, planned_uploads
from tests.fixtures.quick_sections import QUICK_SECTIONS
from tests.fixtures.template_records import template

pytestmark = pytest.mark.integration
GENERAL_DEFINITION: dict[str, Any] = {
    "brief": "Quiet tales about everyday courage.",
    "tone": "calm, wry",
    "tags": {"en": ["calm stories"]},
}


def run_of(harness: Harness, pipeline: Pipeline, story: str) -> Run:
    settings = deep_merged(pipeline.descriptor.default_settings, QUICK_SECTIONS)
    type_id = pipeline.descriptor.type_id
    return executed_run(harness, [pipeline], type_id, settings, smart_writer(name=story))


def assert_complete(run: Run) -> None:
    assert run.status is RunStatus.AWAITING_REVIEW, run.error
    assert all(stage.status is StageStatus.DONE for stage in run.stages)
    assert run.score is not None and run.score > 80
    assert pairs(run, ArtifactKind.METADATA) == PAIRS


def test_a_general_story_template_runs_offline_and_is_not_made_for_kids(harness: Harness) -> None:
    general = template(audience=TemplateAudience.GENERAL, definition=GENERAL_DEFINITION)
    run = run_of(harness, NarratedVideoEngine().pipeline(general), "leaf_boat")
    assert_complete(run)
    metadata = [item for item in run.artifacts if item.meta.get("role") == "upload_metadata"]
    assert metadata and all(item.meta["made_for_kids"] is False for item in metadata)
    english = [text_list(item.meta["tags"]) for item in metadata if item.language == "en"]
    assert english and all(tags == ("calm stories",) for tags in english)
    story_stage = next(stage for stage in run.stages if stage.stage_id == "story")
    assert story_stage.provider != "bundled"
    plans = planned_uploads(harness, run)
    assert plans and not any(plan.made_for_kids for plan in plans)


def test_the_kids_builtin_runs_offline_through_the_engine(harness: Harness) -> None:
    engine = NarratedVideoEngine()
    [builtin] = engine.builtin_templates()
    run = run_of(harness, engine.pipeline(builtin), "golden_mango")
    assert_complete(run)
    plans = planned_uploads(harness, run)
    assert plans and all(plan.made_for_kids for plan in plans)
