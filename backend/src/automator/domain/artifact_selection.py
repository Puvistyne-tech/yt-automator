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
    category_id: str | None = None
    default_language: str | None = None
    hashtags: tuple[str, ...] = ()
    playlist_title: str | None = None


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


def optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def video_metadata(
    artifacts: Sequence[Artifact], language: str, variant: str, fallback_title: str
) -> VideoMetadata:
    found = best_artifact(artifacts, ArtifactKind.METADATA, language, variant)
    meta = found.meta if found is not None else {}
    title = optional_text(meta.get("title"))
    return VideoMetadata(
        title=title or fallback_title,
        description=optional_text(meta.get("description")) or "",
        tags=text_list(meta.get("tags")),
        category_id=optional_text(meta.get("category_id")),
        default_language=optional_text(meta.get("default_language")),
        hashtags=text_list(meta.get("hashtags")),
        playlist_title=optional_text(meta.get("playlist_title")),
    )
