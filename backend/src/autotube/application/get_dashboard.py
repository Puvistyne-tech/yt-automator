from __future__ import annotations

from dataclasses import dataclass

from autotube.application.quota_report import QuotaReport
from autotube.domain.dashboard import DashboardSummary, RecentRun
from autotube.domain.ports import (
    AppSettingsRepository,
    AutomationRepository,
    ChannelRepository,
    Clock,
    CredentialRepository,
    RunRepository,
)
from autotube.domain.run_enums import RunStatus
from autotube.domain.runs import Run, RunQuery
from autotube.shared.clock import local_day_start


def recent(run: Run) -> RecentRun:
    return RecentRun(**run.summary().model_dump(), automation_name=run.automation_name)


@dataclass(frozen=True)
class GetDashboard:
    automations: AutomationRepository
    channels: ChannelRepository
    credentials: CredentialRepository
    runs: RunRepository
    settings: AppSettingsRepository
    quota_report: QuotaReport
    clock: Clock
    recent_limit: int = 10

    def execute(self) -> DashboardSummary:
        automations = self.automations.list()
        today = local_day_start(self.clock.now(), self.settings.get().timezone)
        latest = self.runs.list(RunQuery(limit=self.recent_limit))
        return DashboardSummary(
            automations=len(automations),
            enabled_automations=sum(1 for automation in automations if automation.enabled),
            channels=len(self.channels.list()),
            runs_awaiting_review=len(self.runs.list(RunQuery(status=RunStatus.AWAITING_REVIEW))),
            runs_today=len(self.runs.list(RunQuery(created_after=today))),
            recent_runs=tuple(recent(run) for run in latest),
            quota=tuple(self.quota_report.usage(c) for c in self.credentials.list()),
        )
