from __future__ import annotations

import pytest

from autotube.application.recover_interrupted_runs import (
    INTERRUPTED_RUN_ERROR,
    INTERRUPTED_UPLOAD_ERROR,
    RecoveryReport,
)
from autotube.domain.publish_outcome import NO_UPLOAD_SUCCEEDED
from autotube.domain.run_enums import RunEventKind, RunStatus, StageStatus, UploadStatus
from autotube.domain.run_parts import StageRun, Upload
from autotube.domain.runs import Run
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import recover_runs
from tests.unit.infrastructure.records import run

U = UploadStatus


def upload(status: UploadStatus, error: str | None = None) -> Upload:
    return Upload(
        target_id="t", channel_id="c", language="en", variant="v", status=status, error=error
    )


def stored(harness: Harness, run_id: str) -> Run:
    found = harness.runs.get(run_id)
    assert found is not None
    return found


def test_empty_repositories_recover_nothing(harness: Harness) -> None:
    assert recover_runs(harness).execute() == RecoveryReport((), (), ())
    assert harness.queue.enqueued == [] and harness.events.published == []


def test_running_runs_fail_and_only_their_running_stage_is_marked(harness: Harness) -> None:
    finished = StageRun(
        stage_id="script", title="S", status=StageStatus.DONE, message="ok", finished_at=None
    )
    busy = StageRun(stage_id="render", title="R", status=StageStatus.RUNNING)
    harness.runs.save(run("running", status=RunStatus.RUNNING, stages=(finished, busy)))
    report = recover_runs(harness).execute()
    crashed = stored(harness, "running")
    assert report.failed == ("running",) and report.total() == 1
    assert (crashed.status, crashed.error) == (RunStatus.FAILED, INTERRUPTED_RUN_ERROR)
    assert crashed.finished_at == harness.clock.now()
    assert crashed.stages[0] == finished
    assert crashed.stages[1].status is StageStatus.FAILED
    assert crashed.stages[1].finished_at == harness.clock.now()
    kinds = [event.kind for event in harness.events.published]
    assert kinds == [RunEventKind.STAGE, RunEventKind.STATUS]


@pytest.mark.parametrize(
    ("statuses", "status", "error"),
    [
        ((U.DONE, U.UPLOADING, U.PENDING, U.FAILED), RunStatus.PUBLISHED, None),
        ((U.UPLOADING, U.SKIPPED), RunStatus.APPROVED, NO_UPLOAD_SUCCEEDED),
    ],
)
def test_publishing_runs_settle_and_flag_unfinished_uploads(
    harness: Harness, statuses: tuple[UploadStatus, ...], status: RunStatus, error: str | None
) -> None:
    uploads = tuple(upload(item, "earlier" if item is U.FAILED else None) for item in statuses)
    harness.runs.save(run("publishing", status=RunStatus.PUBLISHING, uploads=uploads))
    report = recover_runs(harness).execute()
    settled = stored(harness, "publishing")
    assert report.settled == ("publishing",)
    assert (settled.status, settled.error) == (status, error)
    for before, after in zip(uploads, settled.uploads, strict=True):
        unfinished = before.status in (U.PENDING, U.UPLOADING)
        assert after.status is (U.FAILED if unfinished else before.status)
        assert after.error == (INTERRUPTED_UPLOAD_ERROR if unfinished else before.error)
    assert harness.events.published[-1].payload["status"] == status.value


def test_queued_runs_are_requeued_oldest_first_and_others_untouched(harness: Harness) -> None:
    harness.runs.save(run("queued-late", 4))
    harness.runs.save(run("queued-early", 3))
    untouched = [
        run(f"other-{status.value}", 5, status=status)
        for status in (RunStatus.AWAITING_REVIEW, RunStatus.APPROVED, RunStatus.CANCELLED)
    ]
    for item in untouched:
        harness.runs.save(item)
    report = recover_runs(harness).execute()
    assert report.requeued == ("queued-early", "queued-late")
    assert harness.queue.enqueued == ["queued-early", "queued-late"]
    assert [stored(harness, item.id) for item in untouched] == untouched
