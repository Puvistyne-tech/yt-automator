from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import partial

from automator.application.automation_presenter import AutomationPresenter
from automator.application.run_recorder import RunRecorder
from automator.application.start_run import StartRun
from automator.domain.automations import Automation
from automator.domain.ports import AutomationRepository, RunRepository
from automator.domain.run_enums import LogLevel, RunStatus, RunTrigger
from automator.domain.run_state import is_unfinished_run
from automator.domain.runs import Run, RunQuery
from automator.shared.clock import find_zone
from automator.shared.errors import AppError

UNFINISHED_STATUSES = (
    RunStatus.QUEUED,
    RunStatus.RUNNING,
    RunStatus.PUBLISHING,
    RunStatus.FAILED,
)


def marked_skip(slot: datetime, stored: Run) -> Run:
    latest = max(slot, stored.skipped_start_at or slot)
    return stored.model_copy(update={"skipped_start_at": latest})


def unfinished_state(run: Run) -> str:
    return "waiting for an automatic retry" if run.status is RunStatus.FAILED else run.status.value


def skip_message(automation: Automation, slot: datetime, blocker: Run) -> str:
    zone = find_zone(automation.schedule.timezone)
    local = slot.astimezone(zone) if zone is not None else slot
    when = f"{local:%Y-%m-%d %H:%M} {automation.schedule.timezone}"
    return (
        f"Scheduled start at {when} skipped: run {blocker.id} is still {unfinished_state(blocker)}"
    )


@dataclass(frozen=True)
class RunDueAutomations:
    automations: AutomationRepository
    presenter: AutomationPresenter
    start_run: StartRun
    runs: RunRepository
    recorder: RunRecorder

    def due_slot(self, automation: Automation, now: datetime) -> datetime | None:
        next_run = self.presenter.next_run_at(automation)
        return next_run if next_run is not None and next_run <= now else None

    def blocking_run(self, automation: Automation) -> Run | None:
        if not automation.schedule.skip_if_unfinished:
            return None
        found = [
            run
            for status in UNFINISHED_STATUSES
            for run in self.runs.list(RunQuery(automation_id=automation.id, status=status))
            if is_unfinished_run(run)
        ]
        return max(found, key=lambda run: run.created_at, default=None)

    def skip(self, automation: Automation, slot: datetime, blocker: Run) -> None:
        newest = self.presenter.latest_run(automation.id) or blocker
        self.runs.update(newest.id, partial(marked_skip, slot))
        self.recorder.log(blocker.id, skip_message(automation, slot, blocker), LogLevel.WARNING)

    def started(self, automation: Automation, now: datetime) -> Run | None:
        slot = self.due_slot(automation, now)
        if slot is None:
            return None
        blocker = self.blocking_run(automation)
        if blocker is not None:
            self.skip(automation, slot, blocker)
            return None
        try:
            return self.start_run.execute(automation.id, RunTrigger.SCHEDULE)
        except AppError:
            return None

    def execute(self, now: datetime) -> list[Run]:
        found = (self.started(automation, now) for automation in self.automations.list())
        return [run for run in found if run is not None]
