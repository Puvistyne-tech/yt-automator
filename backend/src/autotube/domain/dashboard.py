from __future__ import annotations

from autotube.domain.model_base import DomainModel
from autotube.domain.quota import QuotaUsage
from autotube.domain.runs import RunSummary


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
