from __future__ import annotations

from collections.abc import Sequence

from automator.domain.model_base import DomainModel
from automator.domain.run_enums import ArtifactKind
from automator.domain.run_parts import Artifact

EXACT = 2
GENERIC = 1
MISMATCH = 0


class VideoMetadata(DomainModel):
    title: str
    description: str = ""
    tags: tuple[str, ...] = ()


def match_rank(value: str | None, wanted: str) -> int:
    if value == wanted:
        return EXACT
    return GENERIC if value is None else MISMATCH


def artifact_rank(artifact: Artifact, language: str, variant: str) -> int:
    by_language = match_rank(artifact.language, language)
    by_variant = match_rank(artifact.variant, variant)
    return by_language * 10 + by_variant if by_language and by_variant else MISMATCH


def best_artifact(
    artifacts: Sequence[Artifact], kind: ArtifactKind, language: str, variant: str
) -> Artifact | None:
    ranked = [
        (artifact_rank(artifact, language, variant), position, artifact)
        for position, artifact in enumerate(artifacts)
        if artifact.kind is kind
    ]
    eligible = [entry for entry in ranked if entry[0] > MISMATCH]
    return max(eligible, key=lambda entry: (entry[0], entry[1]))[2] if eligible else None


def exact_video(artifacts: Sequence[Artifact], language: str, variant: str) -> Artifact | None:
    candidates = [
        artifact
        for artifact in artifacts
        if artifact.kind is ArtifactKind.VIDEO
        and artifact.language == language
        and artifact.variant == variant
    ]
    return candidates[-1] if candidates else None


def caption_tracks(
    artifacts: Sequence[Artifact], language: str, variant: str
) -> tuple[Artifact, ...]:
    return tuple(
        artifact
        for artifact in artifacts
        if artifact.kind is ArtifactKind.SUBTITLE
        and artifact.language == language
        and match_rank(artifact.variant, variant) > MISMATCH
    )


def text_list(value: object) -> tuple[str, ...]:
    if isinstance(value, list | tuple):
        return tuple(str(item) for item in value)
    return ()


def video_metadata(
    artifacts: Sequence[Artifact], language: str, variant: str, fallback_title: str
) -> VideoMetadata:
    found = best_artifact(artifacts, ArtifactKind.METADATA, language, variant)
    meta = found.meta if found is not None else {}
    title = meta.get("title")
    description = meta.get("description")
    return VideoMetadata(
        title=title if isinstance(title, str) and title else fallback_title,
        description=description if isinstance(description, str) else "",
        tags=text_list(meta.get("tags")),
    )
