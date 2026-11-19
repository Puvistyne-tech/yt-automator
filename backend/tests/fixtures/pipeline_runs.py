from __future__ import annotations

from collections.abc import Sequence

from autotube.application.execute_run import ExecuteRun
from autotube.domain.automations import TargetInput
from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline import Pipeline
from autotube.domain.providers import ProviderConfig, ProviderDescriptor
from autotube.domain.publish_plan import UploadPlan, plan_uploads
from autotube.domain.run_enums import ArtifactKind
from autotube.domain.runs import Run
from autotube.domain.secrets import SecretDefinition
from tests.fixtures.builders import add_automation, target_input
from tests.fixtures.fake_pipeline import FakePipelineRegistry
from tests.fixtures.harness import Harness
from tests.fixtures.kids_fakes import FakeProviders, FakeWriter

VARIANTS = ("episode", "short")
PAIRS = {(language, variant) for language in ("en", "ta") for variant in VARIANTS}
ALL_TARGETS = (
    target_input(language="en", variants=VARIANTS),
    target_input(language="ta", variants=VARIANTS),
)


class KidsCatalog:
    def __init__(self, writer: FakeWriter) -> None:
        self.providers = FakeProviders(writer=writer)
        self.configs: list[list[ProviderConfig]] = []

    def descriptors(self) -> list[ProviderDescriptor]:
        return []

    def secrets(self) -> list[SecretDefinition]:
        return []

    def option_errors(self, configs: Sequence[ProviderConfig]) -> dict[str, str]:  # noqa: ARG002
        return {}

    def resolver(self, configs: Sequence[ProviderConfig]) -> FakeProviders:
        self.configs.append(list(configs))
        return self.providers


def executed_run(
    harness: Harness,
    pipelines: Sequence[Pipeline],
    type_id: str,
    settings: JsonObject,
    writer: FakeWriter,
    targets: tuple[TargetInput, ...] = ALL_TARGETS,
) -> Run:
    harness.pipelines = FakePipelineRegistry(pipelines)
    automation = add_automation(
        harness,
        name="Story run",
        pipeline_type=type_id,
        settings=settings,
        languages=("en", "ta"),
        targets=targets,
    )
    run = harness.start_run.execute(automation.id)
    return ExecuteRun(
        harness.runs,
        harness.pipelines,
        harness.provider_configs,
        KidsCatalog(writer),
        harness.store,
        harness.recorder,
        harness.progress,
        harness.stage_runner,
        harness.auto_publish,
    ).execute(run.id)


def pairs(run: Run, kind: ArtifactKind) -> set[tuple[str | None, str | None]]:
    return {(item.language, item.variant) for item in run.artifacts if item.kind is kind}


def planned_uploads(harness: Harness, run: Run) -> list[UploadPlan]:
    automation = harness.automations.get(run.automation_id)
    assert automation is not None
    pipeline = harness.pipelines.get(automation.pipeline_type)
    assert pipeline is not None
    channel = harness.channels.get("chan-1")
    assert channel is not None
    return plan_uploads(
        run, automation.targets, {channel.id: channel}, pipeline.descriptor, harness.clock.now()
    )
