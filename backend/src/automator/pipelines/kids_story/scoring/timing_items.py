from __future__ import annotations

from collections.abc import Sequence

from automator.domain.quality import ScoreItem
from automator.pipelines.kids_story.artifacts import EPISODE, SHORT, VARIANTS, is_scene_key
from automator.pipelines.kids_story.scoring.inputs import ScoreInputs
from automator.pipelines.kids_story.scoring.measures import (
    SubtitleRules,
    average,
    range_score,
    subtitle_track,
)
from automator.pipelines.kids_story.story.words import word_count
from automator.pipelines.kids_story.timeline.voices import VoiceLine

Lengths = list[tuple[str, float]]


def timeline_keys(inputs: ScoreInputs, language: str, variant: str) -> list[str]:
    found = inputs.video(language, variant)
    entries = found.meta.get("timeline") if found else None
    return [
        str(entry.get("key"))
        for entry in (entries if isinstance(entries, list) else [])
        if isinstance(entry, dict)
    ]


def timeline_lines(inputs: ScoreInputs, language: str, variant: str) -> list[VoiceLine]:
    voices = inputs.voices.get(language, {})
    return [voices[key] for key in timeline_keys(inputs, language, variant) if key in voices]


def narrated_words(inputs: ScoreInputs, language: str, variant: str) -> int:
    return sum(word_count(line.text) for line in timeline_lines(inputs, language, variant))


def subtitle_rules(inputs: ScoreInputs) -> SubtitleRules:
    quality = inputs.settings.quality
    return SubtitleRules(
        min_coverage=quality.subtitle_min_coverage,
        overlap_penalty=quality.subtitle_overlap_penalty,
        out_of_bounds_penalty=quality.subtitle_out_of_bounds_penalty,
    )


def subtitle_timing(inputs: ScoreInputs) -> ScoreItem | None:
    results = []
    for language in inputs.languages:
        for variant in VARIANTS:
            entries = inputs.subtitles(language, variant)
            seconds = inputs.video_seconds(language, variant)
            if entries is None or seconds is None:
                continue
            words = narrated_words(inputs, language, variant)
            measured = subtitle_track(entries, seconds, words, subtitle_rules(inputs))
            results.append((f"{language} {variant}: {measured.detail}", measured.score))
    if not results:
        return None
    return ScoreItem(
        id="subtitle_timing",
        title="Subtitle timing",
        score=average([score for _, score in results]),
        weight=inputs.settings.quality.weights.subtitle_timing,
        detail="; ".join(detail for detail, _ in results),
    )


def duration_item(
    inputs: ScoreInputs, variant: str, found: Lengths, allowed: tuple[float, float]
) -> ScoreItem | None:
    if not found:
        return None
    low, high = allowed
    per_second = inputs.settings.quality.points_lost_per_second
    weights = inputs.settings.quality.weights
    measured = "narration" if variant == EPISODE else "video"
    return ScoreItem(
        id=f"{variant}_duration",
        title="Episode length" if variant == EPISODE else "Short length",
        score=average([range_score(seconds, low, high, per_second) for _, seconds in found]),
        weight=weights.episode_duration if variant == EPISODE else weights.short_duration,
        detail=", ".join(f"{code} {seconds:.0f} s" for code, seconds in found)
        + f" of {measured} (allowed {low:.0f} to {high:.0f} s)",
    )


def narration_seconds(inputs: ScoreInputs, language: str) -> float | None:
    if inputs.video(language, EPISODE) is None:
        return None
    lines = timeline_lines(inputs, language, EPISODE)
    return sum(line.seconds for line in lines if is_scene_key(line.segment))


def episode_duration(inputs: ScoreInputs) -> ScoreItem | None:
    story = inputs.settings.story
    found = [
        (language, seconds)
        for language in inputs.languages
        if (seconds := narration_seconds(inputs, language)) is not None
    ]
    target, tolerance = story.target_duration_seconds, story.duration_tolerance_seconds
    return duration_item(inputs, EPISODE, found, (target - tolerance, target + tolerance))


def short_duration(inputs: ScoreInputs) -> ScoreItem | None:
    if not inputs.settings.short.enabled:
        return None
    found = [
        (language, seconds)
        for language in inputs.languages
        if (seconds := inputs.video_seconds(language, SHORT)) is not None
    ]
    return duration_item(inputs, SHORT, found, (0.0, inputs.settings.short.max_duration_seconds))


def words_per_minute(lines: Sequence[VoiceLine]) -> float | None:
    seconds = sum(line.seconds for line in lines)
    words = sum(word_count(line.text) for line in lines)
    return words * 60.0 / seconds if seconds > 0 and words else None


def speaking_rate(inputs: ScoreInputs) -> ScoreItem | None:
    quality = inputs.settings.quality
    results = []
    for language, voices in inputs.voices.items():
        rate = words_per_minute([line for key, line in voices.items() if is_scene_key(key)])
        if rate is None:
            continue
        low = quality.words_per_minute_min.for_language(language)
        high = quality.words_per_minute_max.for_language(language)
        results.append((language, rate, range_score(rate, low, high, quality.points_lost_per_wpm)))
    if not results:
        return None
    return ScoreItem(
        id="speaking_rate",
        title="Speaking rate",
        score=average([score for _, _, score in results]),
        weight=quality.weights.speaking_rate,
        detail=", ".join(f"{code} {rate:.0f} words per minute" for code, rate, _ in results),
    )
