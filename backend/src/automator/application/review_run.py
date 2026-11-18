from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require
from automator.application.run_progress import RunProgress
from automator.domain.ports import Clock, RunRepository
from automator.domain.run_enums import ReviewDecision, RunStatus
from automator.domain.run_parts import Review
from automator.domain.runs import Run
from automator.shared.errors import RuleConflict

DECIDED_STATUS = {
    ReviewDecision.APPROVED: RunStatus.APPROVED,
    ReviewDecision.REJECTED: RunStatus.REJECTED,
}


@dataclass(frozen=True)
class ReviewRun:
    runs: RunRepository
    progress: RunProgress
    clock: Clock

    def execute(self, run_id: str, decision: ReviewDecision, notes: str = "") -> Run:
        run = require(self.runs.get(run_id), "run", run_id)
        if run.status is not RunStatus.AWAITING_REVIEW:
            raise RuleConflict(
                "run_not_awaiting_review",
                f"run {run.id} is {run.status.value}, not awaiting review",
            )
        review = Review(decision=decision, notes=notes, decided_at=self.clock.now())
        return self.progress.move(
            run.model_copy(update={"review": review}), DECIDED_STATUS[decision]
        )
