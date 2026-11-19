from __future__ import annotations

from dataclasses import dataclass, field

from autotube.application.automation_builder import AutomationBuilder
from autotube.application.automation_presenter import AutomationPresenter
from autotube.application.channel_auth import ChannelAuthorizer
from autotube.application.channel_expiry import ChannelExpiry
from autotube.application.credential_views import CredentialViews
from autotube.application.quota_report import QuotaReport
from autotube.application.run_progress import RunProgress
from autotube.application.run_recorder import RunRecorder
from autotube.domain.diagnostics import DoctorPolicy
from autotube.domain.ports import (
    AppSettingsRepository,
    ArtifactStore,
    AutomationRepository,
    ChannelRepository,
    Clock,
    CredentialRepository,
    EngineCatalog,
    IdGenerator,
    PipelineRegistry,
    ProviderCatalog,
    ProviderConfigRepository,
    QuotaLedger,
    RunEvents,
    RunFileStore,
    RunQueue,
    RunRepository,
    ScheduleCalculator,
    SecretStore,
    SystemInspector,
    TemplateRepository,
    TrendSource,
    YouTubeGateway,
)
from autotube.domain.quota import QuotaPolicy
from autotube.domain.run_parts import RunLogPolicy
from autotube.domain.settings_overrides import doctor_policy, run_log_policy


@dataclass(frozen=True)
class Ports:
    credentials: CredentialRepository
    channels: ChannelRepository
    automations: AutomationRepository
    templates: TemplateRepository
    runs: RunRepository
    provider_configs: ProviderConfigRepository
    app_settings: AppSettingsRepository
    ledger: QuotaLedger
    secrets: SecretStore
    clock: Clock
    ids: IdGenerator
    schedules: ScheduleCalculator
    store: ArtifactStore
    files: RunFileStore
    queue: RunQueue
    events: RunEvents
    pipelines: PipelineRegistry
    engines: EngineCatalog
    catalog: ProviderCatalog
    youtube: YouTubeGateway
    trends: TrendSource
    inspector: SystemInspector
    quota: QuotaPolicy = field(default_factory=QuotaPolicy)
    doctor_policy: DoctorPolicy = field(default_factory=DoctorPolicy)


@dataclass(frozen=True)
class Collaborators:
    authorizer: ChannelAuthorizer
    presenter: AutomationPresenter
    builder: AutomationBuilder
    recorder: RunRecorder
    progress: RunProgress
    quota_report: QuotaReport
    expiry: ChannelExpiry
    credential_views: CredentialViews


def current_log_policy(p: Ports) -> RunLogPolicy:
    return run_log_policy(p.app_settings.get())


def current_doctor_policy(p: Ports) -> DoctorPolicy:
    return doctor_policy(p.doctor_policy, p.app_settings.get())


def collaborators(p: Ports) -> Collaborators:
    recorder = RunRecorder(p.runs, p.events, p.clock, lambda: current_log_policy(p))
    quota_report = QuotaReport(p.ledger, p.clock, p.quota)
    return Collaborators(
        authorizer=ChannelAuthorizer(p.credentials, p.secrets),
        presenter=AutomationPresenter(p.runs, p.schedules),
        builder=AutomationBuilder(p.pipelines, p.channels, p.ids),
        recorder=recorder,
        progress=RunProgress(p.runs, recorder, p.clock),
        quota_report=quota_report,
        expiry=ChannelExpiry(p.channels),
        credential_views=CredentialViews(p.secrets, quota_report),
    )
