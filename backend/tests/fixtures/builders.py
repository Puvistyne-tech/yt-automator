from __future__ import annotations

from typing import Any

from automator.application.create_automation import CreateAutomation
from automator.application.execute_run import ExecuteRun
from automator.domain.automations import Automation, AutomationInput, TargetInput
from automator.domain.channels import Channel, ChannelDefaults, channel_token_secret_name
from automator.domain.credentials import Credential, credential_secret_name
from automator.domain.runs import Run
from tests.fixtures.harness import Harness


def add_credential(
    harness: Harness,
    credential_id: str = "cred-1",
    secret: str | None = "s3cret",
    quota: int = 10000,
) -> Credential:
    credential = Credential(
        id=credential_id,
        name=f"Project {credential_id}",
        client_id=f"client-{credential_id}",
        daily_quota_units=quota,
        created_at=harness.clock.now(),
    )
    harness.credentials.save(credential)
    if secret is not None:
        harness.secrets.set(credential_secret_name(credential_id), secret)
    return credential


def add_channel(
    harness: Harness,
    channel_id: str = "chan-1",
    credential_id: str = "cred-1",
    token: str | None = "tok",
    defaults: ChannelDefaults | None = None,
) -> Channel:
    channel = Channel(
        id=channel_id,
        credential_id=credential_id,
        youtube_channel_id=f"UC-{channel_id}",
        title=f"Channel {channel_id}",
        defaults=defaults or ChannelDefaults(),
        connected_at=harness.clock.now(),
    )
    harness.channels.save(channel)
    if token is not None:
        harness.secrets.set(channel_token_secret_name(channel_id), token)
    return channel


def target_input(channel_id: str = "chan-1", **overrides: Any) -> TargetInput:
    fields: dict[str, Any] = {
        "channel_id": channel_id,
        "language": "en",
        "variants": ("landscape",),
    }
    return TargetInput(**(fields | overrides))


def automation_input(**overrides: Any) -> AutomationInput:
    fields: dict[str, Any] = {
        "name": "Bedtime",
        "pipeline_type": "fake",
        "settings": {"topic": "owls"},
        "languages": ("en",),
        "targets": (target_input(),),
    }
    return AutomationInput(**(fields | overrides))


def create_automation(harness: Harness) -> CreateAutomation:
    return CreateAutomation(
        harness.automations, harness.builder, harness.presenter, harness.ids, harness.clock
    )


def add_automation(harness: Harness, **overrides: Any) -> Automation:
    if harness.credentials.get("cred-1") is None:
        add_credential(harness)
    if harness.channels.get("chan-1") is None:
        add_channel(harness)
    return create_automation(harness).execute(automation_input(**overrides))


def execute_run(harness: Harness) -> ExecuteRun:
    return ExecuteRun(
        harness.runs,
        harness.pipelines,
        harness.provider_configs,
        harness.catalog,
        harness.store,
        harness.recorder,
        harness.progress,
        harness.stage_runner,
        harness.auto_publish,
    )


def started_run(harness: Harness, **overrides: Any) -> Run:
    automation = add_automation(harness, **overrides)
    return harness.start_run.execute(automation.id)


def finished_run(harness: Harness, **overrides: Any) -> Run:
    run = started_run(harness, **overrides)
    return execute_run(harness).execute(run.id)
