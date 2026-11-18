from __future__ import annotations

from datetime import timedelta

import pytest

from autotube.application.retry_due_runs import (
    RetryDueRuns,
    automatic_retry_reset,
    retry_message,
)
from autotube.application.retry_run import RetryRun
from autotube.application.run_progress import Prepare
from autotube.domain.retries import RetryPolicy
from autotube.domain.run_enums import RunStatus, StageStatus
from autotube.domain.runs import Run
from autotube.shared.errors import RuleConflict
from tests.fixtures.builders import execute_run, finished_run
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import retry_run

TWICE = RetryPolicy(auto_retry_count=2, retry_delay_minutes=10)
FAILING = {"fail_stage": "render"}


def retry_due(harness: Harness) -> RetryDueRuns:
    return RetryDueRuns(harness.runs, retry_run(harness), harness.recorder)


def failing_run(harness: Harness, policy: RetryPolicy = TWICE) -> Run:
    return finished_run(harness, settings=FAILING, retry_policy=policy)


def test_a_failed_run_is_retried_after_its_delay_from_the_failed_stage(harness: Harness) -> None:
    failed = failing_run(harness)
    assert failed.retry_at == harness.clock.now() + timedelta(minutes=10)
    assert retry_due(harness).execute(harness.clock.now()) == []
    harness.clock.advance(minutes=10)
    harness.queue.enqueued.clear()
    [queued] = retry_due(harness).execute(harness.clock.now())
    assert queued.status is RunStatus.QUEUED and queued.auto_retries == 1
    assert queued.retry_at is None and harness.queue.enqueued == [failed.id]
    assert [stage.status for stage in queued.stages] == [
        StageStatus.DONE,
        *[StageStatus.PENDING] * 2,
    ]
    assert queued.logs[-1].message == (
        "Automatic retry 1 of 2 from stage render after: stage render failed: render exploded"
    )
    assert queued.auto_retries == 1


def test_retries_stop_when_the_count_is_used(harness: Harness) -> None:
    failed = exhaust_retries(harness, failing_run(harness))
    assert failed.status is RunStatus.FAILED and failed.auto_retries == 2
    assert failed.retry_at is None
    harness.clock.advance(days=1)
    assert retry_due(harness).execute(harness.clock.now()) == []


def exhaust_retries(harness: Harness, failed: Run) -> Run:
    for _ in range(failed.retry_policy.auto_retry_count):
        harness.clock.advance(minutes=10)
        retry_due(harness).execute(harness.clock.now())
        failed = execute_run(harness).execute(failed.id)
    return failed


def test_a_manual_retry_starts_a_fresh_allowance(harness: Harness) -> None:
    exhausted = exhaust_retries(harness, failing_run(harness))
    assert exhausted.auto_retries == 2 and exhausted.retry_at is None
    queued = retry_run(harness).execute(exhausted.id)
    assert queued.auto_retries == 0
    failed = execute_run(harness).execute(exhausted.id)
    assert failed.retry_at == harness.clock.now() + timedelta(minutes=10)
    again = exhaust_retries(harness, failed)
    assert again.status is RunStatus.FAILED and again.auto_retries == 2
    assert again.retry_at is None


def test_a_due_retry_goes_ahead_while_another_run_of_the_automation_runs(
    harness: Harness,
) -> None:
    failed = failing_run(harness)
    other = harness.start_run.execute(failed.automation_id)
    harness.progress.move(other.id, RunStatus.RUNNING)
    harness.clock.advance(minutes=10)
    [queued] = retry_due(harness).execute(harness.clock.now())
    assert queued.id == failed.id and queued.status is RunStatus.QUEUED


def test_a_retry_that_then_succeeds_finishes_normally(harness: Harness) -> None:
    failed = failing_run(harness)
    fixed = {**failed.settings_snapshot, "fail_stage": ""}
    harness.runs.update(failed.id, lambda run: run.model_copy(update={"settings_snapshot": fixed}))
    harness.clock.advance(minutes=10)
    retry_due(harness).execute(harness.clock.now())
    finished = execute_run(harness).execute(failed.id)
    assert finished.status is RunStatus.AWAITING_REVIEW and finished.auto_retries == 1


def test_no_retries_by_default(harness: Harness) -> None:
    failed = failing_run(harness, RetryPolicy())
    assert failed.retry_at is None


def test_a_manual_retry_cancels_the_pending_automatic_one(harness: Harness) -> None:
    failed = failing_run(harness)
    queued = retry_run(harness).execute(failed.id)
    assert queued.retry_at is None
    harness.clock.advance(minutes=10)
    assert retry_due(harness).execute(harness.clock.now()) == []


def test_the_automatic_reset_refuses_a_run_that_is_not_due(harness: Harness) -> None:
    failed = failing_run(harness)
    with pytest.raises(RuleConflict) as raised:
        automatic_retry_reset(harness.clock.now(), failed)
    assert raised.value.code == "retry_not_due"


class RetriedByHandMeanwhile(RetryRun):
    def requeue(self, run_id: str, reset: Prepare) -> Run:
        RetryRun(self.runs, self.store, self.progress, self.queue).execute(run_id)
        return super().requeue(run_id, reset)


def test_a_retry_that_lost_a_race_is_skipped(harness: Harness) -> None:
    failed = failing_run(harness)
    raced = RetriedByHandMeanwhile(harness.runs, harness.store, harness.progress, harness.queue)
    harness.clock.advance(minutes=10)
    assert RetryDueRuns(harness.runs, raced, harness.recorder).execute(harness.clock.now()) == []
    stored = harness.runs.get(failed.id)
    assert stored is not None and stored.status is RunStatus.QUEUED and stored.auto_retries == 0
    assert not any(log.message.startswith("Automatic retry") for log in stored.logs)


def test_retry_messages_name_the_start_when_a_run_has_no_stages(harness: Harness) -> None:
    queued = failing_run(harness).model_copy(update={"stages": (), "auto_retries": 1})
    assert retry_message(queued, None) == "Automatic retry 1 of 2 from stage start after: failure"
