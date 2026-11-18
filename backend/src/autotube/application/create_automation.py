from __future__ import annotations

from dataclasses import dataclass

from autotube.application.automation_builder import AutomationBuilder
from autotube.application.automation_presenter import AutomationPresenter
from autotube.domain.automations import Automation, AutomationInput
from autotube.domain.ports import AutomationRepository, Clock, IdGenerator


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
