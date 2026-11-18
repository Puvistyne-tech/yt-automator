from __future__ import annotations

from dataclasses import dataclass

from autotube.application.lookups import require_automation
from autotube.domain.automation_export import AutomationDocument, automation_document
from autotube.domain.ports import AutomationRepository, ChannelRepository, Clock


@dataclass(frozen=True)
class ExportAutomation:
    automations: AutomationRepository
    channels: ChannelRepository
    clock: Clock

    def execute(self, automation_id: str) -> AutomationDocument:
        automation = require_automation(self.automations, automation_id)
        return automation_document(automation, self.channels.list(), self.clock.now())
