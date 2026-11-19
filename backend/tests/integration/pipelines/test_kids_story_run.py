from __future__ import annotations

import pytest

from autotube.domain.automations import TargetInput
from autotube.domain.run_enums import ArtifactKind, ReviewDecision, RunStatus, StageStatus
from autotube.domain.runs import Run
from autotube.pipelines.registry import installed_pipelines
from tests.fixtures.builders import target_input
from tests.fixtures.harness import Harness
from tests.fixtures.kids_data import quick_settings, smart_writer
from tests.fixtures.pipeline_runs import ALL_TARGETS, PAIRS, executed_run, pairs, planned_uploads
from tests.fixtures.use_cases import publish_run, review_run

pytestmark = pytest.mark.integration


def executed(harness: Harness, targets: tuple[TargetInput, ...] = ALL_TARGETS) -> Run:
    settings = quick_settings().model_dump(mode="json")
    return executed_run(
        harness, installed_pipelines(), "kids_story", settings, smart_writer(), targets
    )


def test_kids_story_runs_end_to_end_and_publishes(harness: Harness) -> None:
    run = executed(harness)
    assert run.status is RunStatus.AWAITING_REVIEW, run.error
    assert all(stage.status is StageStatus.DONE for stage in run.stages)
    assert run.score is not None and run.score > 80
    for kind in (ArtifactKind.THUMBNAIL, ArtifactKind.METADATA, ArtifactKind.SUBTITLE):
        assert pairs(run, kind) == PAIRS
    finals = {
        (item.language, item.variant)
        for item in run.artifacts
        if item.meta.get("role") == "final_video"
    }
    assert finals == PAIRS
    plans = planned_uploads(harness, run)
    assert {(plan.language, plan.variant) for plan in plans} == PAIRS
    for plan in plans:
        assert plan.skip_reason is None and plan.made_for_kids
        assert plan.video is not None and plan.video.meta["role"] == "final_video"
        assert plan.thumbnail is not None and len(plan.captions) == 1
        assert plan.metadata.title and plan.metadata.tags and plan.metadata.description
    approved = review_run(harness).execute(run.id, ReviewDecision.APPROVED)
    assert approved.status is RunStatus.APPROVED
    published = publish_run(harness).execute(run.id)
    assert published.status is RunStatus.PUBLISHED, [upload.error for upload in published.uploads]


def test_a_single_tamil_episode_target_publishes_only_that_video(harness: Harness) -> None:
    run = executed(harness, (target_input(language="ta", variants=("episode",)),))
    plans = planned_uploads(harness, run)
    assert [(plan.language, plan.variant) for plan in plans] == [("ta", "episode")]
    assert plans[0].made_for_kids and plans[0].metadata.title.startswith("கவினும் தங்க மாம்பழமும்")
    review_run(harness).execute(run.id, ReviewDecision.APPROVED)
    published = publish_run(harness).execute(run.id)
    assert published.status is RunStatus.PUBLISHED
    assert [(upload.language, upload.variant) for upload in published.uploads] == [
        ("ta", "episode")
    ]
