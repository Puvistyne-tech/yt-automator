from __future__ import annotations

from automator.domain.quality import ScoreItem
from automator.domain.run_parts import Artifact
from automator.pipelines.kids_story.artifacts import EPISODE, SHORT, Role, latest, text, with_role
from automator.pipelines.kids_story.publishing.limits import (
    DESCRIPTION_MAX,
    TAGS_MAX,
    TITLE_MAX,
    tags_length,
)
from automator.pipelines.kids_story.scoring.inputs import ScoreInputs
from automator.pipelines.kids_story.scoring.measures import FULL, average, clamp, distance_outside


def within_limits(found: Artifact) -> bool:
    title = text(found.meta.get("title"))
    description = text(found.meta.get("description"))
    raw_tags = found.meta.get("tags")
    tags = [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []
    return (
        0 < len(title) <= TITLE_MAX
        and len(description) <= DESCRIPTION_MAX
        and tags_length(tags) <= TAGS_MAX
        and found.meta.get("made_for_kids") is True
    )


def metadata_limits(inputs: ScoreInputs) -> ScoreItem | None:
    found = with_role(inputs.artifacts, Role.UPLOAD_METADATA)
    if not found:
        return None
    good = sum(1 for item in found if within_limits(item))
    return ScoreItem(
        id="metadata_limits",
        title="Metadata limits",
        score=FULL * good / len(found),
        weight=inputs.settings.quality.weights.metadata_limits,
        detail=f"{good} of {len(found)} uploads within YouTube limits and made for kids",
    )


def loudness_score(inputs: ScoreInputs, video: Artifact) -> float | None:
    if inputs.media is None:
        return None
    try:
        measured = inputs.media.loudness_lufs(inputs.path(video))
    except Exception:
        return None
    quality = inputs.settings.quality
    target = inputs.settings.episode.loudness_lufs
    tolerance = quality.loudness_tolerance_lu
    beyond = distance_outside(measured, target - tolerance, target + tolerance)
    return clamp(FULL - beyond * quality.points_lost_per_lu)


def loudness(inputs: ScoreInputs) -> ScoreItem | None:
    videos = with_role(inputs.artifacts, Role.FINAL_VIDEO)
    scores = [score for video in videos if (score := loudness_score(inputs, video)) is not None]
    if not scores:
        return None
    return ScoreItem(
        id="loudness",
        title="Loudness",
        score=average(scores),
        weight=inputs.settings.quality.weights.loudness,
        detail=f"{len(scores)} videos against {inputs.settings.episode.loudness_lufs} LUFS",
    )


def expected_roles(inputs: ScoreInputs) -> list[Role]:
    roles = [Role.FINAL_VIDEO, Role.THUMBNAIL, Role.UPLOAD_METADATA]
    subtitles = inputs.settings.subtitles
    if subtitles.enabled and subtitles.upload_captions:
        roles.append(Role.CAPTION_TRACK)
    return roles


def completeness(inputs: ScoreInputs) -> ScoreItem:
    variants = [EPISODE, SHORT] if inputs.settings.short.enabled else [EPISODE]
    wanted = [
        (language, variant, role)
        for language in inputs.languages
        for variant in variants
        for role in expected_roles(inputs)
    ]
    missing = [
        f"{role.value} {language} {variant}"
        for language, variant, role in wanted
        if latest(inputs.artifacts, role, language, variant) is None
    ]
    return ScoreItem(
        id="completeness",
        title="Every output present",
        score=FULL * (len(wanted) - len(missing)) / len(wanted) if wanted else FULL,
        weight=inputs.settings.quality.weights.completeness,
        detail="missing: " + ", ".join(missing) if missing else "all outputs present",
    )
