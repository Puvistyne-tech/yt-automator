from __future__ import annotations

from dataclasses import dataclass

from autotube.application.automation_builder import AutomationBuilder
from autotube.application.automation_presenter import AutomationPresenter
from autotube.application.lookups import require_automation
from autotube.domain.automations import Automation, AutomationInput
from autotube.domain.ports import AutomationRepository, Clock


@dataclass(frozen=True)
class UpdateAutomation:
    automations: AutomationRepository
    builder: AutomationBuilder
    presenter: AutomationPresenter
    clock: Clock

    def execute(self, automation_id: str, data: AutomationInput) -> Automation:
        current = require_automation(self.automations, automation_id)
        updated = self.builder.build(data, current.id, current.created_at, self.clock.now())
        self.automations.save(updated)
        return self.presenter.present(updated)
