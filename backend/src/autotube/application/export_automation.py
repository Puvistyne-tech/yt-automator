from __future__ import annotations

from dataclasses import dataclass

from autotube.application.lookups import descriptor_of, require_automation
from autotube.domain.automation_export import AutomationDocument, automation_document
from autotube.domain.machine_local import portable_settings
from autotube.domain.ports import (
    AutomationRepository,
    ChannelRepository,
    Clock,
    PipelineRegistry,
)


@dataclass(frozen=True)
class ExportAutomation:
    automations: AutomationRepository
    channels: ChannelRepository
    pipelines: PipelineRegistry
    clock: Clock

    def execute(self, automation_id: str) -> AutomationDocument:
        automation = require_automation(self.automations, automation_id)
        descriptor = descriptor_of(self.pipelines.get(automation.pipeline_type))
        settings = portable_settings(automation.settings, descriptor)
        portable = automation.model_copy(update={"settings": settings})
        return automation_document(portable, self.channels.list(), self.clock.now())
