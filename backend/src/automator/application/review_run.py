from __future__ import annotations

from dataclasses import dataclass
from functools import partial

from automator.application.auto_publish import publishes_on_approval
from automator.application.lookups import require_run
from automator.application.run_progress import RunProgress
from automator.domain.ports import Clock, RunQueue, RunRepository
from automator.domain.run_enums import ReviewDecision, RunStatus
from automator.domain.run_parts import Review
from automator.domain.runs import Run
from automator.shared.errors import RuleConflict

DECIDED_STATUS = {
    ReviewDecision.APPROVED: RunStatus.APPROVED,
    ReviewDecision.REJECTED: RunStatus.REJECTED,
}


def reviewed(review: Review, stored: Run) -> Run:
    if stored.status is not RunStatus.AWAITING_REVIEW:
        raise RuleConflict(
            "run_not_awaiting_review",
            f"run {stored.id} is {stored.status.value}, not awaiting review",
        )
    return stored.model_copy(update={"review": review})


@dataclass(frozen=True)
class ReviewRun:
    runs: RunRepository
    progress: RunProgress
    clock: Clock
    queue: RunQueue

    def execute(self, run_id: str, decision: ReviewDecision, notes: str = "") -> Run:
        run = require_run(self.runs, run_id)
        review = Review(decision=decision, notes=notes, decided_at=self.clock.now())
        decided = self.progress.move(
            run.id, DECIDED_STATUS[decision], prepare=partial(reviewed, review)
        )
        if publishes_on_approval(decided):
            self.queue.enqueue(decided.id)
        return decided
