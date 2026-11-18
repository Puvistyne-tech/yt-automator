from __future__ import annotations

from dataclasses import dataclass

from automator.application.automation_presenter import AutomationPresenter
from automator.application.lookups import require
from automator.domain.automations import Automation
from automator.domain.ports import AutomationRepository, Clock


@dataclass(frozen=True)
class SetAutomationEnabled:
    automations: AutomationRepository
    presenter: AutomationPresenter
    clock: Clock

    def execute(self, automation_id: str, enabled: bool) -> Automation:
        current = require(self.automations.get(automation_id), "automation", automation_id)
        if current.enabled == enabled:
            return self.presenter.present(current)
        updated = current.model_copy(update={"enabled": enabled, "updated_at": self.clock.now()})
        self.automations.save(updated)
        return self.presenter.present(updated)
