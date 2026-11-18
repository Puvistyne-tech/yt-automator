from __future__ import annotations

from datetime import UTC, datetime
from itertools import product

import pytest

from automator.domain.run_enums import RunStatus
from automator.domain.run_state import ALLOWED_TRANSITIONS, can_transition, transition
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
