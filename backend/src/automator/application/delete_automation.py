from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require_automation
from automator.domain.ports import AutomationRepository


@dataclass(frozen=True)
class DeleteAutomation:
    automations: AutomationRepository

    def execute(self, automation_id: str) -> None:
        require_automation(self.automations, automation_id)
        self.automations.delete(automation_id)
