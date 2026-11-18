from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require
from automator.domain.ports import AutomationRepository


@dataclass(frozen=True)
class DeleteAutomation:
    automations: AutomationRepository

    def execute(self, automation_id: str) -> None:
        require(self.automations.get(automation_id), "automation", automation_id)
        self.automations.delete(automation_id)
