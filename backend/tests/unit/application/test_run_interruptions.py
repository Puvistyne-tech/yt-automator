from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import pytest

from automator.domain.pipeline import StageContext
from automator.domain.run_enums import LogLevel, RunEventKind, RunStatus, StageStatus
from automator.domain.run_state import transition
from tests.fixtures.builders import execute_run, finished_run, started_run
from tests.fixtures.fake_pipeline import FakePipeline, FakePipelineRegistry
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import cancel_run, delete_run, retry_run


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


def test_synced_marks_runs_missing_from_the_repository_as_cancelled(harness: Harness) -> None:
    run = started_run(harness)
    harness.runs.delete(run.id)
    moved = run.model_copy(update={"status": RunStatus.RUNNING})
    assert harness.progress.synced(moved) == run.model_copy(update={"status": RunStatus.CANCELLED})
    assert harness.progress.owned(moved) is None


def cancel_and_retry_from(harness: Harness) -> Callable[[StageContext], None]:
    def cancel_then_retry(context: StageContext) -> None:
        cancel_run(harness).execute(context.run_id)
        retry_run(harness).execute(context.run_id)

    return cancel_then_retry


@pytest.mark.parametrize("fail_stage", ["", "script"])
def test_cancel_then_immediate_retry_keeps_the_retried_run(
    harness: Harness, fail_stage: str
) -> None:
    run = started_run(harness, settings={"fail_stage": fail_stage})
    with_hook(harness, 0, cancel_and_retry_from(harness))
    execute_run(harness).execute(run.id)
    stored = harness.runs.get(run.id)
    assert stored is not None and stored.status is RunStatus.QUEUED and stored.error is None
    assert [s.status for s in stored.stages] == [P, P, P]
    assert stored.artifacts == ()
    assert list(harness.store.workspace(run.id).glob("script-*")) == []
    assert harness.queue.enqueued == [run.id, run.id]
    harness.pipelines = FakePipelineRegistry([harness.pipeline])
    harness.runs.save(stored.model_copy(update={"settings_snapshot": {"topic": "owls"}}))
    assert execute_run(harness).execute(run.id).status is RunStatus.AWAITING_REVIEW


def cancel_and_delete_from(harness: Harness) -> Callable[[StageContext], None]:
    def cancel_then_delete(context: StageContext) -> None:
        cancel_run(harness).execute(context.run_id)
        delete_run(harness).execute(context.run_id)

    return cancel_then_delete


def test_a_run_deleted_during_a_stage_is_not_recreated(harness: Harness) -> None:
    run = started_run(harness)
    pipeline = with_hook(harness, 0, cancel_and_delete_from(harness))
    result = execute_run(harness).execute(run.id)
    assert result.status is RunStatus.CANCELLED
    assert harness.runs.get(run.id) is None
    assert pipeline.stage_list[1].calls == []


def test_logs_are_stored_with_level_and_stage(harness: Harness) -> None:
    harness.pipelines = FakePipelineRegistry([replace(harness.pipeline, score_warning="dim")])
    run = finished_run(harness)
    entries = [(log.level, log.stage_id, log.message) for log in run.logs]
    assert entries == [
        (LogLevel.INFO, "script", "script running"),
        (LogLevel.INFO, "render", "render running"),
        (LogLevel.INFO, "package", "package running"),
        (LogLevel.WARNING, None, "dim"),
    ]
    payloads = [e.payload for e in harness.events.published if e.kind is RunEventKind.LOG]
    assert payloads[-1] == {"level": "warning", "stage_id": None, "message": "dim"}


def test_logging_for_a_missing_run_only_emits_the_event(harness: Harness) -> None:
    harness.recorder.log("gone", "hello", LogLevel.ERROR, "script")
    assert harness.runs.get("gone") is None
    assert harness.events.published[-1].payload == {
        "level": "error",
        "stage_id": "script",
        "message": "hello",
    }
