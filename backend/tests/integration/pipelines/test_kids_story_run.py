from __future__ import annotations

from collections.abc import Sequence

import pytest

from automator.application.execute_run import ExecuteRun
from automator.domain.providers import ProviderConfig, ProviderDescriptor
from automator.domain.publish_plan import plan_uploads
from automator.domain.run_enums import ArtifactKind, ReviewDecision, RunStatus, StageStatus
from automator.domain.runs import Run
from automator.domain.secrets import SecretDefinition
from automator.pipelines.registry import build_pipeline_registry
from tests.fixtures.builders import add_automation, target_input
from tests.fixtures.fake_pipeline import FakePipelineRegistry
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import publish_run, review_run
from tests.unit.pipelines.kids_data import quick_settings, smart_writer
from tests.unit.pipelines.kids_fakes import FakeProviders

pytestmark = pytest.mark.integration
VARIANTS = ("episode", "short")
PAIRS = {(language, variant) for language in ("en", "ta") for variant in VARIANTS}


class KidsCatalog:
    def __init__(self) -> None:
        self.providers = FakeProviders(writer=smart_writer())
        self.configs: list[list[ProviderConfig]] = []

    def descriptors(self) -> list[ProviderDescriptor]:
        return []

    def secrets(self) -> list[SecretDefinition]:
        return []

    def resolver(self, configs: Sequence[ProviderConfig]) -> FakeProviders:
        self.configs.append(list(configs))
        return self.providers


def executed(harness: Harness) -> Run:
    harness.pipelines = FakePipelineRegistry(build_pipeline_registry().list())
    automation = add_automation(
        harness,
        name="Kutty Stories",
        pipeline_type="kids_story",
        settings=quick_settings().model_dump(mode="json"),
        languages=("en", "ta"),
        targets=(
            target_input(language="en", variants=VARIANTS),
            target_input(language="ta", variants=VARIANTS),
        ),
    )
    run = harness.start_run.execute(automation.id)
    return ExecuteRun(
        harness.runs,
        harness.pipelines,
        harness.provider_configs,
        KidsCatalog(),
        harness.store,
        harness.recorder,
        harness.progress,
        harness.stage_runner,
    ).execute(run.id)


def pairs(run: Run, kind: ArtifactKind) -> set[tuple[str | None, str | None]]:
    return {(item.language, item.variant) for item in run.artifacts if item.kind is kind}


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
    automation = harness.automations.get(run.automation_id)
    assert automation is not None
    descriptor = harness.pipelines.get("kids_story")
    assert descriptor is not None
    channel = harness.channels.get("chan-1")
    assert channel is not None
    plans = plan_uploads(
        run, automation.targets, {channel.id: channel}, descriptor.descriptor, harness.clock.now()
    )
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
