from __future__ import annotations

import json
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

from pydantic import JsonValue

from automator.domain.model_base import JsonObject
from automator.domain.pipeline import NewArtifact, StageContext
from automator.domain.run_enums import ArtifactKind
from automator.domain.run_parts import Artifact

ROLE = "role"
EPISODE = "episode"
SHORT = "short"
VARIANTS = (EPISODE, SHORT)
SCENE_PREFIX = "scene-"


class Role(StrEnum):
    STORY = "story"
    CHARACTER_SHEET = "character_sheet"
    CANDIDATE = "candidate"
    VISUAL = "visual"
    THUMBNAIL_ART = "thumbnail_art"
    NARRATION = "narration"
    CLIP = "clip"
    MUSIC = "music"
    SOUND_EFFECT = "sound_effect"
    CAPTIONS = "captions"
    FINAL_VIDEO = "final_video"
    COMPOSITION = "composition"
    THUMBNAIL = "thumbnail"
    UPLOAD_METADATA = "upload_metadata"
    CAPTION_TRACK = "caption_track"
    STYLE = "style"


class MissingArtifactError(RuntimeError):
    pass


def matches(
    artifact: Artifact, role: Role, language: str | None, variant: str | None, meta: JsonObject
) -> bool:
    if artifact.meta.get(ROLE) != role.value:
        return False
    if language is not None and artifact.language != language:
        return False
    if variant is not None and artifact.variant != variant:
        return False
    return all(artifact.meta.get(key) == value for key, value in meta.items())


def with_role(
    artifacts: Sequence[Artifact],
    role: Role,
    language: str | None = None,
    variant: str | None = None,
    **meta: JsonValue,
) -> list[Artifact]:
    return [item for item in artifacts if matches(item, role, language, variant, meta)]


def latest(
    artifacts: Sequence[Artifact],
    role: Role,
    language: str | None = None,
    variant: str | None = None,
    **meta: JsonValue,
) -> Artifact | None:
    found = with_role(artifacts, role, language, variant, **meta)
    return found[-1] if found else None


def required(
    artifacts: Sequence[Artifact],
    role: Role,
    language: str | None = None,
    variant: str | None = None,
    **meta: JsonValue,
) -> Artifact:
    found = latest(artifacts, role, language, variant, **meta)
    if found is None:
        wanted = ", ".join(f"{key}={value}" for key, value in meta.items())
        where = f"{language or 'any'} {variant or 'any'} {wanted}"
        raise MissingArtifactError(f"missing {role.value} artifact for {where}")
    return found


def path_of(context: StageContext, artifact: Artifact) -> Path:
    return context.workspace / artifact.filename


def folder(context: StageContext, name: str) -> Path:
    path = context.workspace / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: JsonValue) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact(
    kind: ArtifactKind,
    path: Path,
    media_type: str,
    role: Role,
    language: str | None = None,
    variant: str | None = None,
    **meta: JsonValue,
) -> NewArtifact:
    return NewArtifact(
        kind=kind,
        path=path,
        language=language,
        variant=variant,
        media_type=media_type,
        meta={ROLE: role.value, **meta},
    )


def visual_key(segment: str, variant: str) -> str:
    return f"{segment}@{variant}"


def scene_key(index: int) -> str:
    return f"{SCENE_PREFIX}{index}"


def is_scene_key(key: str) -> bool:
    return key.startswith(SCENE_PREFIX)


def scene_visual_key(index: int, variant: str) -> str:
    return visual_key(scene_key(index), variant)


def active_variants(short_enabled: bool) -> tuple[str, ...]:
    return VARIANTS if short_enabled else (EPISODE,)


def number(value: JsonValue, default: float = 0.0) -> float:
    return float(value) if isinstance(value, int | float) else default


def text(value: JsonValue) -> str:
    return value if isinstance(value, str) else ""
