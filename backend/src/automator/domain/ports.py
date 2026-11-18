from __future__ import annotations

from automator.domain.port_catalogs import PipelineRegistry, ProviderCatalog
from automator.domain.port_repositories import (
    AppSettingsRepository,
    AutomationRepository,
    ChannelRepository,
    CredentialRepository,
    ProviderConfigRepository,
    RunChange,
    RunRepository,
)
from automator.domain.port_runtime import (
    ArtifactStore,
    Clock,
    IdGenerator,
    QuotaLedger,
    RunEvents,
    RunQueue,
    ScheduleCalculator,
    SecretStore,
    SystemInspector,
)
from automator.domain.port_youtube import YouTubeGateway

__all__ = [
    "AppSettingsRepository",
    "ArtifactStore",
    "AutomationRepository",
    "ChannelRepository",
    "Clock",
    "CredentialRepository",
    "IdGenerator",
    "PipelineRegistry",
    "ProviderCatalog",
    "ProviderConfigRepository",
    "QuotaLedger",
    "RunChange",
    "RunEvents",
    "RunQueue",
    "RunRepository",
    "ScheduleCalculator",
    "SecretStore",
    "SystemInspector",
    "YouTubeGateway",
]
