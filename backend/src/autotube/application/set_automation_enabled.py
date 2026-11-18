from __future__ import annotations

from dataclasses import dataclass

from autotube.application.automation_presenter import AutomationPresenter
from autotube.application.lookups import require_automation
from autotube.domain.automations import Automation
from autotube.domain.ports import AutomationRepository, Clock


@dataclass(frozen=True)
class SetAutomationEnabled:
    automations: AutomationRepository
    presenter: AutomationPresenter
    clock: Clock

    def execute(self, automation_id: str, enabled: bool) -> Automation:
        current = require_automation(self.automations, automation_id)
        if current.enabled == enabled:
            return self.presenter.present(current)
        updated = current.model_copy(update={"enabled": enabled, "updated_at": self.clock.now()})
        self.automations.save(updated)
        return self.presenter.present(updated)
