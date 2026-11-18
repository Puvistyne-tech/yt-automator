from __future__ import annotations

from automator.domain.model_base import DomainModel
from automator.domain.quota import QuotaUsage
from automator.domain.runs import RunSummary


class RecentRun(RunSummary):
    automation_name: str


class DashboardSummary(DomainModel):
    automations: int
    enabled_automations: int
    channels: int
    runs_awaiting_review: int
    runs_today: int
    recent_runs: tuple[RecentRun, ...]
    quota: tuple[QuotaUsage, ...]
