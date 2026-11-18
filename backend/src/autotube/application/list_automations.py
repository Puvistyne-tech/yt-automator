from __future__ import annotations

from dataclasses import dataclass

from autotube.application.automation_presenter import AutomationPresenter
from autotube.domain.automations import Automation
from autotube.domain.ports import AutomationRepository


@dataclass(frozen=True)
class ListAutomations:
    automations: AutomationRepository
    presenter: AutomationPresenter

    def execute(self) -> list[Automation]:
        ordered = sorted(self.automations.list(), key=lambda item: item.name.casefold())
        return [self.presenter.present(automation) for automation in ordered]
