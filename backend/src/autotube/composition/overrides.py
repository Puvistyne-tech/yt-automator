from __future__ import annotations

from dataclasses import dataclass

from autotube.domain.ports import (
    Clock,
    EngineCatalog,
    IdGenerator,
    PipelineRegistry,
    ProviderCatalog,
    RunEvents,
    SecretStore,
    SystemInspector,
    YouTubeGateway,
)


@dataclass(frozen=True)
class Overrides:
    youtube: YouTubeGateway | None = None
    catalog: ProviderCatalog | None = None
    pipelines: PipelineRegistry | None = None
    engines: EngineCatalog | None = None
    secrets: SecretStore | None = None
    clock: Clock | None = None
    ids: IdGenerator | None = None
    events: RunEvents | None = None
    inspector: SystemInspector | None = None
