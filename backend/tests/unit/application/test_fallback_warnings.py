from __future__ import annotations

from dataclasses import replace

import pytest

from autotube.application.run_recorder import RunRecorder
from autotube.application.stage_runner import StageRunner
from autotube.domain.capabilities import Capability
from autotube.domain.pipeline import StageContext
from autotube.domain.provider_fallbacks import ProviderFallback
from autotube.domain.run_enums import LogLevel, StageStatus
from autotube.domain.run_parts import RunLogPolicy
from autotube.domain.runs import Run
from tests.fixtures.builders import execute_run, finished_run, started_run
from tests.fixtures.fake_pipeline import FakePipelineRegistry
from tests.fixtures.harness import Harness

LONG_REASON = "x" * 100
GATED = ProviderFallback(
    capability=Capability.IMAGE, failed="mflux", used="offline_image", reason=LONG_REASON
)


def falling_back_at(harness: Harness, index: int) -> None:
    def fall_back(_: StageContext) -> None:
        harness.catalog.fallen_back.extend([GATED, GATED])

    stages = list(harness.pipeline.stage_list)
    stages[index] = replace(stages[index], hook=fall_back)
    harness.pipelines = FakePipelineRegistry([replace(harness.pipeline, stage_list=tuple(stages))])


def warnings_of(run: Run) -> list[tuple[str | None, str]]:
    return [(log.stage_id, log.message) for log in run.logs if log.level is LogLevel.WARNING]


def run_with_reason_chars(harness: Harness, reason_chars: int) -> Run:
    policy = RunLogPolicy(fallback_reason_chars=reason_chars)
    recorder = RunRecorder(harness.runs, harness.events, harness.clock, lambda: policy)
    runner = StageRunner(harness.store, recorder, harness.progress, harness.ids, harness.clock)
    run = started_run(harness)
    return replace(execute_run(harness), stage_runner=runner).execute(run.id)


@pytest.mark.parametrize(
    ("fail_stage", "status"), [("", StageStatus.DONE), ("render", StageStatus.FAILED)]
)
def test_a_stage_that_fell_back_logs_one_warning_tagged_with_it(
    harness: Harness, fail_stage: str, status: StageStatus
) -> None:
    falling_back_at(harness, 1)
    run = finished_run(harness, settings={"topic": "owls", "fail_stage": fail_stage})
    assert [stage_id for stage_id, _ in warnings_of(run)] == ["render"]
    assert run.stages[1].status is status


def test_the_runner_cuts_the_reason_at_the_configured_length(harness: Harness) -> None:
    falling_back_at(harness, 0)
    [(_, warning)] = warnings_of(run_with_reason_chars(harness, 20))
    assert f"({'x' * 19}…)" in warning


def test_no_fallback_means_no_warning(harness: Harness) -> None:
    assert warnings_of(finished_run(harness)) == []
