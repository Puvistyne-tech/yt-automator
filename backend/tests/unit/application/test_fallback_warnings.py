from __future__ import annotations

from dataclasses import replace

import pytest

from autotube.domain.capabilities import Capability
from autotube.domain.pipeline import StageContext
from autotube.domain.provider_fallbacks import ProviderFallback
from autotube.domain.run_enums import LogLevel, StageStatus
from autotube.domain.runs import Run
from tests.fixtures.builders import finished_run
from tests.fixtures.fake_pipeline import FakePipelineRegistry
from tests.fixtures.harness import Harness

GATED = ProviderFallback(
    capability=Capability.IMAGE,
    failed="mflux",
    used="offline_image",
    reason="GatedRepoError: 403 Client Error.\nCannot access gated repo",
)
EXPECTED = (
    "image provider mflux failed (GatedRepoError: 403 Client Error.); "
    "used offline_image instead for 2 calls"
)


def falling_back_at(harness: Harness, index: int) -> None:
    def fall_back(_: StageContext) -> None:
        harness.catalog.fallen_back.extend([GATED, GATED])

    stages = list(harness.pipeline.stage_list)
    stages[index] = replace(stages[index], hook=fall_back)
    harness.pipelines = FakePipelineRegistry([replace(harness.pipeline, stage_list=tuple(stages))])


def warnings_of(run: Run) -> list[tuple[str | None, str]]:
    return [(log.stage_id, log.message) for log in run.logs if log.level is LogLevel.WARNING]


@pytest.mark.parametrize(
    ("fail_stage", "status"), [("", StageStatus.DONE), ("render", StageStatus.FAILED)]
)
def test_a_stage_that_fell_back_logs_one_warning_for_it(
    harness: Harness, fail_stage: str, status: StageStatus
) -> None:
    falling_back_at(harness, 1)
    run = finished_run(harness, settings={"topic": "owls", "fail_stage": fail_stage})
    assert warnings_of(run) == [("render", EXPECTED)]
    assert run.stages[1].status is status


def test_no_fallback_means_no_warning(harness: Harness) -> None:
    assert warnings_of(finished_run(harness)) == []
