from __future__ import annotations

from automator.domain.automations import Automation
from automator.domain.channels import Channel
from automator.domain.credentials import Credential
from automator.domain.pipeline import Pipeline
from automator.domain.pipeline_descriptors import PipelineDescriptor
from automator.domain.ports import (
    AutomationRepository,
    ChannelRepository,
    CredentialRepository,
    RunRepository,
)
from automator.domain.runs import Run
from automator.shared.errors import NotFound


def require[T](value: T | None, entity: str, entity_id: str) -> T:
    if value is None:
        raise NotFound(entity, entity_id)
    return value


def require_run(runs: RunRepository, run_id: str) -> Run:
    return require(runs.get(run_id), "run", run_id)


def require_automation(automations: AutomationRepository, automation_id: str) -> Automation:
    return require(automations.get(automation_id), "automation", automation_id)


def require_credential(credentials: CredentialRepository, credential_id: str) -> Credential:
    return require(credentials.get(credential_id), "credential", credential_id)


def require_channel(channels: ChannelRepository, channel_id: str) -> Channel:
    return require(channels.get(channel_id), "channel", channel_id)


def descriptor_of(pipeline: Pipeline | None) -> PipelineDescriptor | None:
    return pipeline.descriptor if pipeline is not None else None
