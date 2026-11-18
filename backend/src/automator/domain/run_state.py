from __future__ import annotations

from datetime import datetime

from automator.domain.run_enums import RunStatus
from automator.domain.runs import Run
from automator.shared.errors import RuleConflict

S = RunStatus

ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    S.QUEUED: frozenset({S.RUNNING, S.FAILED, S.CANCELLED}),
    S.RUNNING: frozenset({S.AWAITING_REVIEW, S.APPROVED, S.FAILED, S.CANCELLED}),
    S.AWAITING_REVIEW: frozenset({S.APPROVED, S.REJECTED, S.QUEUED, S.CANCELLED}),
    S.APPROVED: frozenset({S.PUBLISHING, S.QUEUED, S.CANCELLED}),
    S.REJECTED: frozenset({S.QUEUED}),
    S.PUBLISHING: frozenset({S.PUBLISHED, S.APPROVED}),
    S.PUBLISHED: frozenset(),
    S.FAILED: frozenset({S.QUEUED}),
    S.CANCELLED: frozenset({S.QUEUED}),
}

FINISHED_STATUSES = frozenset(
    {S.AWAITING_REVIEW, S.APPROVED, S.REJECTED, S.PUBLISHED, S.FAILED, S.CANCELLED}
)
ACTIVE_STATUSES = frozenset({S.QUEUED, S.RUNNING, S.PUBLISHING})


def can_transition(current: RunStatus, target: RunStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_transition(run: Run, target: RunStatus) -> None:
    if not can_transition(run.status, target):
        raise RuleConflict(
            "invalid_run_transition",
            f"run {run.id} cannot move from {run.status.value} to {target.value}",
        )


def transition(run: Run, target: RunStatus, at: datetime, error: str | None = None) -> Run:
    ensure_transition(run, target)
    changes: dict[str, object] = {"status": target, "error": error}
    if target is S.RUNNING:
        changes["started_at"] = run.started_at or at
    if target is S.QUEUED:
        changes |= {"started_at": None, "finished_at": None}
    if target in FINISHED_STATUSES:
        changes["finished_at"] = at
    return run.model_copy(update=changes)


STAGE_RESULT_STATUSES = frozenset({S.RUNNING, S.CANCELLED})


def accepts_stage_results(status: RunStatus) -> bool:
    return status in STAGE_RESULT_STATUSES
