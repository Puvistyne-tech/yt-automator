from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from autotube.domain.pipeline import StageContext
from autotube.domain.run_enums import RunEventKind, RunStatus
from autotube.domain.runs import Run
from tests.fixtures.builders import execute_run, started_run
from tests.fixtures.fake_pipeline import FakePipeline, FakePipelineRegistry
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import cancel_run, delete_run, retry_run
from tests.unit.application.test_run_interruptions import with_hook

Hook = Callable[[StageContext], None]


def cancels(harness: Harness, delete: bool = False) -> Hook:
    def hook(context: StageContext) -> None:
        cancel_run(harness).execute(context.run_id)
        if delete:
            delete_run(harness).execute(context.run_id)

    return hook


def cancels_and_retries(harness: Harness, from_stage: str | None = None) -> Hook:
    def hook(context: StageContext) -> None:
        cancel_run(harness).execute(context.run_id)
        retry_run(harness).execute(context.run_id, from_stage)

    return hook


def stored(harness: Harness, run_id: str) -> Run:
    found = harness.runs.get(run_id)
    assert found is not None
    return found


def scoring_with(harness: Harness, hook: Hook, raise_on_score: bool = False) -> FakePipeline:
    pipeline = replace(harness.pipeline, score_hook=hook, raise_on_score=raise_on_score)
    harness.pipelines = FakePipelineRegistry([pipeline])
    return pipeline


def statuses(harness: Harness, run_id: str) -> list[object]:
    return [
        event.payload["status"]
        for event in harness.events.published
        if event.run_id == run_id and event.kind is RunEventKind.STATUS
    ]


def test_cancel_during_a_logging_stage_stays_cancelled(harness: Harness) -> None:
    run = started_run(harness)
    with_hook(harness, 0, cancels(harness))
    execute_run(harness).execute(run.id)
    final = stored(harness, run.id)
    assert final.status is RunStatus.CANCELLED
    assert [log.message for log in final.logs] == ["script running"]


def test_cancel_then_retry_during_a_logging_stage_keeps_and_runs_the_retry(
    harness: Harness,
) -> None:
    run = started_run(harness)
    with_hook(harness, 0, cancels_and_retries(harness))
    execute_run(harness).execute(run.id)
    assert stored(harness, run.id).status is RunStatus.QUEUED
    assert stored(harness, run.id).artifacts == ()
    harness.pipelines = FakePipelineRegistry([harness.pipeline])
    assert execute_run(harness).execute(run.id).status is RunStatus.AWAITING_REVIEW


def test_cancel_during_scoring_keeps_the_run_cancelled_without_a_score(harness: Harness) -> None:
    run = started_run(harness)
    scoring_with(harness, cancels(harness))
    result = execute_run(harness).execute(run.id)
    final = stored(harness, run.id)
    assert result == final
    assert (final.status, final.score, final.score_details) == (RunStatus.CANCELLED, None, ())
    assert "awaiting_review" not in statuses(harness, run.id)


def test_cancel_and_delete_during_scoring_does_not_recreate_the_run(harness: Harness) -> None:
    run = started_run(harness)
    scoring_with(harness, cancels(harness, delete=True))
    assert execute_run(harness).execute(run.id).status is RunStatus.CANCELLED
    assert harness.runs.get(run.id) is None


def test_scoring_failure_after_a_retry_leaves_the_retried_run_queued(harness: Harness) -> None:
    run = started_run(harness)
    scoring_with(harness, cancels_and_retries(harness, "render"), raise_on_score=True)
    execute_run(harness).execute(run.id)
    final = stored(harness, run.id)
    assert (final.status, final.error) == (RunStatus.QUEUED, None)
    assert "failed" not in statuses(harness, run.id)


def test_a_run_deleted_during_a_stage_leaves_no_folder(harness: Harness) -> None:
    run = started_run(harness)
    with_hook(harness, 0, cancels(harness, delete=True))
    execute_run(harness).execute(run.id)
    assert harness.runs.get(run.id) is None
    assert not (harness.store.root / run.id).exists()


def test_a_stale_stage_discards_only_unreferenced_files(harness: Harness) -> None:
    run = started_run(harness)
    with_hook(harness, 1, cancels_and_retries(harness, "render"))
    execute_run(harness).execute(run.id)
    final = stored(harness, run.id)
    workspace = harness.store.workspace(run.id)
    assert final.status is RunStatus.QUEUED
    assert {a.stage_id for a in final.artifacts} == {"script"}
    assert (workspace / "script-en.txt").exists()
    assert not (workspace / "en-landscape.mp4").exists()


def test_a_run_deleted_during_a_failing_stage_leaves_no_folder(harness: Harness) -> None:
    run = started_run(harness, settings={"fail_stage": "script"})
    with_hook(harness, 0, cancels(harness, delete=True))
    assert execute_run(harness).execute(run.id).status is RunStatus.CANCELLED
    assert harness.runs.get(run.id) is None
    assert not (harness.store.root / run.id).exists()
