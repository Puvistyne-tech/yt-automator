from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import product

import pytest

from automator.domain.retries import RetryPolicy
from automator.domain.run_enums import RunStatus
from automator.domain.run_state import (
    ALLOWED_TRANSITIONS,
    accepts_stage_results,
    can_transition,
    is_unfinished_run,
    retry_due,
    transition,
)
from automator.domain.runs import Run
from automator.shared.errors import RuleConflict

S = RunStatus
CREATED = datetime(2026, 1, 5, 9, tzinfo=UTC)
AT = datetime(2026, 1, 5, 10, tzinfo=UTC)

EXPECTED_EDGES = {
    (S.QUEUED, S.RUNNING),
    (S.QUEUED, S.FAILED),
    (S.QUEUED, S.CANCELLED),
    (S.RUNNING, S.AWAITING_REVIEW),
    (S.RUNNING, S.APPROVED),
    (S.RUNNING, S.REJECTED),
    (S.RUNNING, S.FAILED),
    (S.RUNNING, S.CANCELLED),
    (S.AWAITING_REVIEW, S.APPROVED),
    (S.AWAITING_REVIEW, S.REJECTED),
    (S.AWAITING_REVIEW, S.QUEUED),
    (S.AWAITING_REVIEW, S.CANCELLED),
    (S.APPROVED, S.PUBLISHING),
    (S.APPROVED, S.QUEUED),
    (S.APPROVED, S.CANCELLED),
    (S.REJECTED, S.QUEUED),
    (S.PUBLISHING, S.PUBLISHED),
    (S.PUBLISHING, S.APPROVED),
    (S.FAILED, S.QUEUED),
    (S.CANCELLED, S.QUEUED),
}


def make_run(status: RunStatus) -> Run:
    return Run(
        id="r1",
        automation_id="a1",
        automation_name="A",
        pipeline_type="fake",
        status=status,
        languages=("en",),
        settings_snapshot={},
        created_at=CREATED,
        started_at=CREATED,
        finished_at=CREATED,
    )


def test_every_status_has_a_transition_entry() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(RunStatus)


@pytest.mark.parametrize(("current", "target"), list(product(RunStatus, RunStatus)))
def test_transition_table(current: RunStatus, target: RunStatus) -> None:
    allowed = (current, target) in EXPECTED_EDGES
    assert can_transition(current, target) is allowed
    if allowed:
        assert transition(make_run(current), target, AT).status is target
    else:
        with pytest.raises(RuleConflict, match="cannot move"):
            transition(make_run(current), target, AT)


def test_running_keeps_first_start_and_clears_finish_on_requeue() -> None:
    queued = transition(make_run(S.FAILED), S.QUEUED, AT)
    assert (queued.started_at, queued.finished_at) == (None, None)
    running = transition(queued, S.RUNNING, AT)
    assert running.started_at == AT and running.finished_at is None


@pytest.mark.parametrize("target", [S.AWAITING_REVIEW, S.APPROVED, S.FAILED, S.CANCELLED])
def test_finishing_sets_finished_at_and_error(target: RunStatus) -> None:
    finished = transition(make_run(S.RUNNING), target, AT, error="why")
    assert finished.finished_at == AT and finished.error == "why"


def test_transition_does_not_mutate_the_original() -> None:
    original = make_run(S.QUEUED)
    transition(original, S.RUNNING, AT)
    assert original.status is S.QUEUED


@pytest.mark.parametrize("status", list(RunStatus))
def test_only_running_and_cancelled_runs_accept_stage_results(status: RunStatus) -> None:
    accepted = {RunStatus("running"), RunStatus("cancelled")}
    assert accepts_stage_results(status) is (status in accepted)


def retrying_run(status: RunStatus, retries: int = 2, used: int = 0) -> Run:
    policy = RetryPolicy(auto_retry_count=retries, retry_delay_minutes=15)
    return make_run(status).model_copy(update={"retry_policy": policy, "auto_retries": used})


def test_failing_schedules_an_automatic_retry_while_retries_remain() -> None:
    failed = transition(retrying_run(S.RUNNING), S.FAILED, AT, error="boom")
    assert failed.retry_at == AT + timedelta(minutes=15)


def test_failing_without_retries_left_schedules_nothing() -> None:
    assert transition(retrying_run(S.RUNNING, used=2), S.FAILED, AT).retry_at is None
    assert transition(make_run(S.RUNNING), S.FAILED, AT).retry_at is None


def test_requeueing_clears_a_pending_retry() -> None:
    failed = transition(retrying_run(S.RUNNING), S.FAILED, AT)
    assert transition(failed, S.QUEUED, AT).retry_at is None


def test_a_retry_is_due_only_for_a_failed_run_at_or_after_its_time() -> None:
    failed = transition(retrying_run(S.RUNNING), S.FAILED, AT)
    due_at = AT + timedelta(minutes=15)
    assert retry_due(failed, due_at) is True
    assert retry_due(failed, due_at - timedelta(seconds=1)) is False
    assert retry_due(failed.model_copy(update={"status": S.QUEUED}), due_at) is False
    assert retry_due(make_run(S.FAILED), due_at) is False


@pytest.mark.parametrize(
    ("status", "unfinished"),
    [
        (S.QUEUED, True),
        (S.RUNNING, True),
        (S.PUBLISHING, True),
        (S.AWAITING_REVIEW, False),
        (S.APPROVED, False),
        (S.FAILED, False),
        (S.PUBLISHED, False),
    ],
)
def test_unfinished_runs(status: RunStatus, unfinished: bool) -> None:
    assert is_unfinished_run(make_run(status)) is unfinished


def test_a_failed_run_waiting_for_its_retry_is_unfinished() -> None:
    assert is_unfinished_run(transition(retrying_run(S.RUNNING), S.FAILED, AT)) is True


def test_runs_stored_before_retries_existed_load_with_none_pending() -> None:
    new_fields = {"retry_policy", "auto_retries", "retry_at", "skipped_start_at"}
    stored = make_run(S.FAILED).model_dump(mode="json", exclude=new_fields)
    loaded = Run.model_validate(stored)
    assert (loaded.retry_policy, loaded.auto_retries, loaded.retry_at) == (RetryPolicy(), 0, None)
    assert loaded.skipped_start_at is None
