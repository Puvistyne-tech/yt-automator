from __future__ import annotations

from dataclasses import dataclass, field

from automator.application.automation_builder import AutomationBuilder
from automator.application.automation_presenter import AutomationPresenter
from automator.application.channel_auth import ChannelAuthorizer
from automator.application.quota_report import QuotaReport
from automator.application.run_progress import RunProgress
from automator.application.run_recorder import RunRecorder
from automator.domain.ports import (
    AppSettingsRepository,
    ArtifactStore,
    AutomationRepository,
    ChannelRepository,
    Clock,
    CredentialRepository,
    IdGenerator,
    PipelineRegistry,
    ProviderCatalog,
    ProviderConfigRepository,
    QuotaLedger,
    RunEvents,
    RunQueue,
    RunRepository,
    ScheduleCalculator,
    SecretStore,
    YouTubeGateway,
)
from automator.domain.quota import QuotaPolicy


@dataclass(frozen=True)
class Ports:
    credentials: CredentialRepository
    channels: ChannelRepository
    automations: AutomationRepository
    runs: RunRepository
    provider_configs: ProviderConfigRepository
    app_settings: AppSettingsRepository
    ledger: QuotaLedger
    secrets: SecretStore
    clock: Clock
    ids: IdGenerator
    schedules: ScheduleCalculator
    store: ArtifactStore
    queue: RunQueue
    events: RunEvents
    pipelines: PipelineRegistry
    catalog: ProviderCatalog
    youtube: YouTubeGateway
    quota: QuotaPolicy = field(default_factory=QuotaPolicy)


@dataclass(frozen=True)
class Collaborators:
    authorizer: ChannelAuthorizer
    presenter: AutomationPresenter
    builder: AutomationBuilder
    recorder: RunRecorder
    progress: RunProgress
    quota_report: QuotaReport


def collaborators(p: Ports) -> Collaborators:
    recorder = RunRecorder(p.runs, p.events, p.clock)
    return Collaborators(
        authorizer=ChannelAuthorizer(p.credentials, p.secrets),
        presenter=AutomationPresenter(p.runs, p.schedules),
        builder=AutomationBuilder(p.pipelines, p.channels, p.ids),
        recorder=recorder,
        progress=RunProgress(p.runs, recorder, p.clock),
        quota_report=QuotaReport(p.ledger, p.clock, p.quota),
    )
