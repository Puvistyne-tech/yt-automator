from __future__ import annotations

from dataclasses import dataclass

from autotube.application.automation_presenter import AutomationPresenter
from autotube.application.lookups import require_automation
from autotube.domain.automations import Automation
from autotube.domain.ports import AutomationRepository


@dataclass(frozen=True)
class GetAutomation:
    automations: AutomationRepository
    presenter: AutomationPresenter

    def execute(self, automation_id: str) -> Automation:
        automation = require_automation(self.automations, automation_id)
        return self.presenter.present(automation)
