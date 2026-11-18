from __future__ import annotations

from dataclasses import dataclass

from automator.application.automation_presenter import AutomationPresenter
from automator.application.lookups import require_automation
from automator.domain.automations import Automation
from automator.domain.ports import AutomationRepository


@dataclass(frozen=True)
class GetAutomation:
    automations: AutomationRepository
    presenter: AutomationPresenter

    def execute(self, automation_id: str) -> Automation:
        automation = require_automation(self.automations, automation_id)
        return self.presenter.present(automation)
