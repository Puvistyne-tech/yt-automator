from __future__ import annotations

from autotube.domain.artifact_selection import text_list
from autotube.domain.quality import ScoreItem
from autotube.domain.run_parts import Artifact
from autotube.domain.upload_details import DESCRIPTION_MAX_BYTES, utf8_length
from autotube.pipelines.narrated_video.art.stand_ins import STAND_IN_FOR
from autotube.pipelines.narrated_video.artifacts import (
    EPISODE,
    Role,
    active_variants,
    latest,
    text,
    with_role,
)
from autotube.pipelines.narrated_video.publishing.limits import TAGS_MAX, TITLE_MAX, tags_length
from autotube.pipelines.narrated_video.scoring.inputs import ScoreInputs
from autotube.pipelines.narrated_video.scoring.measures import (
    FULL,
    average,
    clamp,
    distance_outside,
)


def within_limits(found: Artifact, made_for_kids: bool) -> bool:
    title = text(found.meta.get("title"))
    description = text(found.meta.get("description"))
    return (
        0 < len(title) <= TITLE_MAX
        and utf8_length(description) <= DESCRIPTION_MAX_BYTES
        and tags_length(text_list(found.meta.get("tags"))) <= TAGS_MAX
        and found.meta.get("made_for_kids") is made_for_kids
    )


def audience_note(made_for_kids: bool) -> str:
    return "made for kids" if made_for_kids else "not made for kids"


def metadata_limits(inputs: ScoreInputs) -> ScoreItem | None:
    found = with_role(inputs.artifacts, Role.UPLOAD_METADATA)
    if not found:
        return None
    made_for_kids = inputs.settings.safety.for_kids
    good = sum(1 for item in found if within_limits(item, made_for_kids))
    return ScoreItem(
        id="metadata_limits",
        title="Metadata limits",
        score=FULL * good / len(found),
        weight=inputs.settings.quality.weights.metadata_limits,
        detail=f"{good} of {len(found)} uploads within YouTube limits and "
        f"{audience_note(made_for_kids)}",
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
    if inputs.settings.subtitles.captions_uploaded:
        roles.append(Role.CAPTION_TRACK)
    return roles


def completeness(inputs: ScoreInputs) -> ScoreItem:
    variants = active_variants(inputs.settings.short.enabled)
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


def episode_pictures(inputs: ScoreInputs) -> list[Artifact]:
    visuals = with_role(inputs.artifacts, Role.VISUAL, variant=EPISODE)
    latest_by_key = {item.meta.get("visual_key"): item for item in visuals if "scene" in item.meta}
    return list(latest_by_key.values())


def stand_in_detail(stand_ins: list[Artifact], total: int) -> str:
    if not stand_ins:
        return f"all {total} episode pictures came from the chosen image model"
    failed = sorted({name for item in stand_ins for name in text_list(item.meta.get(STAND_IN_FOR))})
    return (
        f"{len(stand_ins)} of {total} episode pictures are stand-ins drawn after "
        f"{', '.join(failed)} failed"
    )


def real_pictures(inputs: ScoreInputs) -> ScoreItem | None:
    pictures = episode_pictures(inputs)
    if not pictures:
        return None
    stand_ins = [item for item in pictures if text_list(item.meta.get(STAND_IN_FOR))]
    return ScoreItem(
        id="real_pictures",
        title="Pictures from the chosen image model",
        score=FULL * (len(pictures) - len(stand_ins)) / len(pictures),
        weight=inputs.settings.quality.weights.real_pictures,
        detail=stand_in_detail(stand_ins, len(pictures)),
    )
