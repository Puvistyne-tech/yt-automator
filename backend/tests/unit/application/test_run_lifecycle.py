from __future__ import annotations

import pytest

from autotube.application.get_run import GetRun
from autotube.application.list_runs import ListRuns
from autotube.application.open_run_artifact import OpenRunArtifact
from autotube.domain.run_enums import ReviewDecision, RunStatus, StageStatus
from autotube.domain.runs import RunQuery
from autotube.shared.errors import NotFound, RuleConflict, ValidationFailed
from tests.fixtures.builders import add_automation, execute_run, finished_run, started_run
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import cancel_run, delete_run, failed_at_render, retry_run, review_run


def test_retry_defaults_to_first_unfinished_stage_and_keeps_earlier_artifacts(
    harness: Harness,
) -> None:
    failed = failed_at_render(harness)
    script_artifacts = failed.artifacts
    retried = retry_run(harness).execute(failed.id)
    assert retried.status is RunStatus.QUEUED and retried.error is None
    assert [s.status for s in retried.stages] == [
        StageStatus.DONE,
        StageStatus.PENDING,
        StageStatus.PENDING,
    ]
    assert retried.artifacts == script_artifacts
    assert harness.queue.enqueued[-1] == failed.id


def test_retry_from_chosen_stage_discards_its_and_later_artifacts(harness: Harness) -> None:
    done = finished_run(harness)
    retried = retry_run(harness).execute(done.id, from_stage="render")
    assert {a.stage_id for a in retried.artifacts} == {"script"}
    discarded = {a.id for a in done.artifacts if a.stage_id != "script"}
    assert set(harness.store.discarded) == discarded
    assert retried.score is None and retried.review is None and retried.uploads == ()
    rerun = execute_run(harness).execute(done.id)
    assert rerun.status is RunStatus.AWAITING_REVIEW
    assert harness.pipeline.stage_list[0].calls == [done.id]
    assert harness.pipeline.stage_list[1].calls == [done.id, done.id]


def test_retry_with_everything_done_restarts_from_first_stage(harness: Harness) -> None:
    done = finished_run(harness)
    retried = retry_run(harness).execute(done.id)
    assert all(s.status is StageStatus.PENDING for s in retried.stages) and retried.artifacts == ()


def test_retry_rejects_unknown_stage_and_active_runs(harness: Harness) -> None:
    failed = failed_at_render(harness)
    with pytest.raises(ValidationFailed) as raised:
        retry_run(harness).execute(failed.id, from_stage="nope")
    assert "from_stage" in raised.value.fields
    queued = harness.start_run.execute(failed.automation_id)
    with pytest.raises(RuleConflict):
        retry_run(harness).execute(queued.id)
    with pytest.raises(NotFound):
        retry_run(harness).execute("missing")


@pytest.mark.parametrize("finish", [False, True])
def test_cancel_marks_run_and_signals_queue(harness: Harness, finish: bool) -> None:
    run = finished_run(harness) if finish else started_run(harness)
    cancelled = cancel_run(harness).execute(run.id)
    assert cancelled.status is RunStatus.CANCELLED and cancelled.finished_at is not None
    assert harness.queue.cancelled == [run.id]


def test_cancel_refuses_finished_runs(harness: Harness) -> None:
    failed = failed_at_render(harness)
    with pytest.raises(RuleConflict):
        cancel_run(harness).execute(failed.id)


@pytest.mark.parametrize(
    ("decision", "status"),
    [(ReviewDecision.APPROVED, RunStatus.APPROVED), (ReviewDecision.REJECTED, RunStatus.REJECTED)],
)
def test_review_records_decision(
    harness: Harness, decision: ReviewDecision, status: RunStatus
) -> None:
    run = finished_run(harness)
    reviewed = review_run(harness).execute(run.id, decision, "nice")
    assert reviewed.status is status
    assert reviewed.review is not None and reviewed.review.notes == "nice"
    assert reviewed.review.decided_at == harness.clock.now()


def test_review_only_when_awaiting(harness: Harness) -> None:
    run = started_run(harness)
    with pytest.raises(RuleConflict) as raised:
        review_run(harness).execute(run.id, ReviewDecision.APPROVED)
    assert raised.value.code == "run_not_awaiting_review"


def test_delete_run_removes_record_and_files(harness: Harness) -> None:
    run = finished_run(harness)
    workspace = harness.store.workspace(run.id)
    delete_run(harness).execute(run.id)
    assert harness.runs.get(run.id) is None and not workspace.exists()
    with pytest.raises(NotFound):
        delete_run(harness).execute(run.id)


def test_delete_refuses_active_run(harness: Harness) -> None:
    run = started_run(harness)
    with pytest.raises(RuleConflict):
        delete_run(harness).execute(run.id)


def test_list_runs_newest_first_with_filters(harness: Harness) -> None:
    first = add_automation(harness, name="First")
    second = add_automation(harness, name="Second")
    runs = []
    for automation_id in (first.id, second.id, first.id):
        harness.clock.advance(minutes=1)
        runs.append(harness.start_run.execute(automation_id))
    assert [r.id for r in ListRuns(harness.runs).execute()] == [r.id for r in reversed(runs)]
    only_first = ListRuns(harness.runs).execute(RunQuery(automation_id=first.id))
    assert [r.id for r in only_first] == [runs[2].id, runs[0].id]
    assert ListRuns(harness.runs).execute(RunQuery(status=RunStatus.FAILED)) == []


@pytest.mark.parametrize(
    ("default_limit", "query_limit", "count"), [(2, None, 2), (2, 3, 3), (50, 1, 1)]
)
def test_list_runs_limit(
    harness: Harness, default_limit: int, query_limit: int | None, count: int
) -> None:
    automation = add_automation(harness)
    for _ in range(4):
        harness.clock.advance(seconds=1)
        harness.start_run.execute(automation.id)
    listed = ListRuns(harness.runs, default_limit=default_limit).execute(
        RunQuery(limit=query_limit)
    )
    assert len(listed) == count


def test_get_run_and_open_artifact(harness: Harness) -> None:
    run = finished_run(harness)
    assert GetRun(harness.runs).execute(run.id) == run
    artifact, path = OpenRunArtifact(harness.runs, harness.store).execute(
        run.id, run.artifacts[0].id
    )
    assert artifact == run.artifacts[0] and path.read_text(encoding="utf-8") == "story about owls"
    with pytest.raises(NotFound):
        OpenRunArtifact(harness.runs, harness.store).execute(run.id, "nope")
    with pytest.raises(NotFound):
        GetRun(harness.runs).execute("nope")


def test_delete_removes_the_row_before_the_folder(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = failed_at_render(harness)
    rows_at_folder_removal: list[object] = []
    remove_folder = harness.store.delete_run

    def recording_delete(run_id: str) -> None:
        rows_at_folder_removal.append(harness.runs.get(run_id))
        remove_folder(run_id)

    monkeypatch.setattr(harness.store, "delete_run", recording_delete)
    delete_run(harness).execute(run.id)
    assert rows_at_folder_removal == [None]
