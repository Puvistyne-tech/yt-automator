from __future__ import annotations

from dataclasses import dataclass

from automator.application.automation_presenter import AutomationPresenter
from automator.domain.automations import Automation
from automator.domain.ports import AutomationRepository


@dataclass(frozen=True)
class ListAutomations:
    automations: AutomationRepository
    presenter: AutomationPresenter

    def execute(self) -> list[Automation]:
        ordered = sorted(self.automations.list(), key=lambda item: item.name.casefold())
        return [self.presenter.present(automation) for automation in ordered]
