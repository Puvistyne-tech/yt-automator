from __future__ import annotations

from dataclasses import dataclass

from automator.application.automation_builder import AutomationBuilder
from automator.application.automation_presenter import AutomationPresenter
from automator.domain.automations import Automation, AutomationInput
from automator.domain.ports import AutomationRepository, Clock, IdGenerator


@dataclass(frozen=True)
class CreateAutomation:
    automations: AutomationRepository
    builder: AutomationBuilder
    presenter: AutomationPresenter
    ids: IdGenerator
    clock: Clock

    def execute(self, data: AutomationInput) -> Automation:
        now = self.clock.now()
        automation = self.builder.build(data, self.ids.new(), now, now)
        self.automations.save(automation)
        return self.presenter.present(automation)
