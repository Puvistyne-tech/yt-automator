from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from automator.application.lookups import descriptor_of, require
from automator.domain.automation_rules import automation_errors, normalized_settings
from automator.domain.automations import Automation, AutomationInput, Target
from automator.domain.kids_rules import enforce_kids_content
from automator.domain.pipeline import Pipeline
from automator.domain.ports import ChannelRepository, IdGenerator, PipelineRegistry
from automator.shared.errors import raise_if_invalid


@dataclass(frozen=True)
class AutomationBuilder:
    pipelines: PipelineRegistry
    channels: ChannelRepository
    ids: IdGenerator

    def validated_pipeline(self, data: AutomationInput) -> Pipeline:
        pipeline = self.pipelines.get(data.pipeline_type)
        settings_model = pipeline.settings_model if pipeline is not None else None
        channel_ids = {channel.id for channel in self.channels.list()}
        errors = automation_errors(data, descriptor_of(pipeline), settings_model, channel_ids)
        raise_if_invalid(errors)
        return require(pipeline, "pipeline", data.pipeline_type)

    def targets(self, data: AutomationInput, pipeline: Pipeline) -> tuple[Target, ...]:
        return tuple(
            Target(**target.model_dump(exclude={"id"}), id=target.id or self.ids.new())
            for target in enforce_kids_content(data.targets, pipeline.descriptor)
        )

    def build(
        self, data: AutomationInput, automation_id: str, created_at: datetime, now: datetime
    ) -> Automation:
        pipeline = self.validated_pipeline(data)
        fields = data.model_dump(exclude={"targets", "settings"})
        return Automation(
            **fields,
            id=automation_id,
            settings=normalized_settings(pipeline.settings_model, data.settings),
            targets=self.targets(data, pipeline),
            created_at=created_at,
            updated_at=now,
        )
