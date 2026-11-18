from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import pytest

from automator.domain.pipeline import StageContext
from automator.domain.run_enums import RunStatus, StageStatus
from automator.domain.run_state import transition
from tests.fixtures.builders import execute_run, started_run
from tests.fixtures.fake_pipeline import FakePipeline, FakePipelineRegistry
from tests.fixtures.harness import Harness


def with_hook(harness: Harness, index: int, hook: Callable[[StageContext], None]) -> FakePipeline:
    stages = list(harness.pipeline.stage_list)
    stages[index] = replace(stages[index], hook=hook)
    pipeline = replace(harness.pipeline, stage_list=tuple(stages))
    harness.pipelines = FakePipelineRegistry([pipeline])
    return pipeline


def cancel_from(harness: Harness) -> Callable[[StageContext], None]:
    def cancel_midway(context: StageContext) -> None:
        stored = harness.runs.get(context.run_id)
        assert stored is not None
        harness.runs.save(transition(stored, RunStatus.CANCELLED, harness.clock.now()))

    return cancel_midway


D, F, P = StageStatus.DONE, StageStatus.FAILED, StageStatus.PENDING


@pytest.mark.parametrize(
    ("index", "fail_stage", "stages"),
    [(0, "", [D, P, P]), (0, "script", [F, P, P]), (2, "", [D, D, D])],
)
def test_cancellation_during_a_stage_stops_the_run(
    harness: Harness, index: int, fail_stage: str, stages: list[StageStatus]
) -> None:
    run = started_run(harness, settings={"fail_stage": fail_stage})
    pipeline = with_hook(harness, index, cancel_from(harness))
    result = execute_run(harness).execute(run.id)
    assert result.status is RunStatus.CANCELLED and result.error is None
    assert harness.runs.get(run.id) == result
    assert [s.status for s in result.stages] == stages
    assert pipeline.score_calls == []
    assert all(stage.calls == [] for stage in pipeline.stage_list[index + 1 :])


def raise_bare(_context: StageContext) -> None:
    raise ConnectionError


def test_stage_error_without_message_is_named_by_its_class(harness: Harness) -> None:
    run = started_run(harness)
    with_hook(harness, 0, raise_bare)
    result = execute_run(harness).execute(run.id)
    assert result.stages[0].message == "ConnectionError"
    assert result.error == "stage script failed: ConnectionError"


def test_synced_returns_runs_missing_from_the_repository_unchanged(harness: Harness) -> None:
    run = started_run(harness)
    harness.runs.delete(run.id)
    moved = run.model_copy(update={"status": RunStatus.RUNNING})
    assert harness.progress.synced(moved) is moved
