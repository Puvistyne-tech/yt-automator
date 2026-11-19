from __future__ import annotations

from collections.abc import Sequence

from autotube.domain.capabilities import Capability
from autotube.domain.pipeline import NewArtifact
from autotube.domain.provider_fallbacks import ProviderFallback, stand_in_sources

DRAWN_BY = "provider"
STAND_IN_FOR = "stand_in_for"


def marked_stand_in(item: NewArtifact, fallbacks: Sequence[ProviderFallback]) -> NewArtifact:
    drawn_by = item.meta.get(DRAWN_BY)
    if not isinstance(drawn_by, str):
        return item
    replaced: list[str] = stand_in_sources(fallbacks, Capability.IMAGE, drawn_by)
    if not replaced:
        return item
    return item.model_copy(update={"meta": {**item.meta, STAND_IN_FOR: replaced}})


def with_stand_ins(
    made: Sequence[NewArtifact], fallbacks: Sequence[ProviderFallback]
) -> list[NewArtifact]:
    return [marked_stand_in(item, fallbacks) for item in made]
