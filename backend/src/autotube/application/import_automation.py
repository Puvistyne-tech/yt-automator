from __future__ import annotations

from dataclasses import dataclass

from autotube.application.automation_builder import AutomationBuilder
from autotube.application.create_automation import CreateAutomation
from autotube.domain.automation_export import (
    ChannelChoices,
    ImportPreview,
    channel_choice_errors,
    imported_input,
    missing_choice_errors,
    read_document,
    refusal_message,
    resolved_channels,
    unresolved_channels,
    without_missing_channel_errors,
)
from autotube.domain.automations import Automation
from autotube.domain.model_base import JsonObject
from autotube.domain.ports import ChannelRepository
from autotube.domain.validation import prefixed
from autotube.shared.errors import ValidationFailed, raise_if_invalid


@dataclass(frozen=True)
class ImportAutomation:
    channels: ChannelRepository
    builder: AutomationBuilder
    create: CreateAutomation

    def checked(
        self, raw: JsonObject, chosen: ChannelChoices
    ) -> tuple[ImportPreview, dict[str, str]]:
        document, problems = read_document(raw)
        if document is None:
            raise ValidationFailed(problems, refusal_message(problems))
        channels = self.channels.list()
        local = {channel.id for channel in channels}
        mapping = resolved_channels(document, channels, chosen)
        data = imported_input(document, mapping)
        rule_errors = without_missing_channel_errors(self.builder.errors(data), data, local)
        errors = channel_choice_errors(chosen, local) | prefixed(rule_errors, "automation")
        unknown = unresolved_channels(document, mapping)
        return ImportPreview(automation=data, unknown_channels=unknown), errors

    def preview(self, raw: JsonObject, chosen: ChannelChoices) -> ImportPreview:
        preview, errors = self.checked(raw, chosen)
        raise_if_invalid(errors)
        return preview

    def execute(self, raw: JsonObject, chosen: ChannelChoices) -> Automation:
        preview, errors = self.checked(raw, chosen)
        raise_if_invalid(errors | missing_choice_errors(preview.unknown_channels))
        return self.create.execute(preview.automation)
