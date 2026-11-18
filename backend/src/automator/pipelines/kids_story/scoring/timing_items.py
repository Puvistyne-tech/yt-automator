from __future__ import annotations

from automator.domain.quality import ScoreItem
from automator.pipelines.kids_story.artifacts import EPISODE, SHORT, VARIANTS
from automator.pipelines.kids_story.scoring.inputs import ScoreInputs
from automator.pipelines.kids_story.scoring.measures import average, range_score, subtitle_track
from automator.pipelines.kids_story.timeline.voices import VoiceLine


def timeline_keys(inputs: ScoreInputs, language: str, variant: str) -> list[str]:
    found = inputs.video(language, variant)
    entries = found.meta.get("timeline") if found else None
    return [
        str(entry.get("key"))
        for entry in (entries if isinstance(entries, list) else [])
        if isinstance(entry, dict)
    ]


def narrated_words(inputs: ScoreInputs, language: str, variant: str) -> int:
    voices = inputs.voices.get(language, {})
    return sum(
        len(voices[key].words) for key in timeline_keys(inputs, language, variant) if key in voices
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
            measured = subtitle_track(
                entries, seconds, words, inputs.settings.quality.subtitle_min_coverage
            )
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


def duration_item(inputs: ScoreInputs, variant: str, low: float, high: float) -> ScoreItem | None:
    per_second = inputs.settings.quality.points_lost_per_second
    found = [
        (language, seconds)
        for language in inputs.languages
        if (seconds := inputs.video_seconds(language, variant)) is not None
    ]
    if not found:
        return None
    weights = inputs.settings.quality.weights
    return ScoreItem(
        id=f"{variant}_duration",
        title="Episode length" if variant == EPISODE else "Short length",
        score=average([range_score(seconds, low, high, per_second) for _, seconds in found]),
        weight=weights.episode_duration if variant == EPISODE else weights.short_duration,
        detail=", ".join(f"{code} {seconds:.0f} s" for code, seconds in found)
        + f" (allowed {low:.0f} to {high:.0f} s)",
    )


def episode_duration(inputs: ScoreInputs) -> ScoreItem | None:
    story = inputs.settings.story
    low = story.target_duration_seconds - story.duration_tolerance_seconds
    high = story.target_duration_seconds + story.duration_tolerance_seconds
    return duration_item(inputs, EPISODE, low, high)


def short_duration(inputs: ScoreInputs) -> ScoreItem | None:
    if not inputs.settings.short.enabled:
        return None
    return duration_item(inputs, SHORT, 0.0, inputs.settings.short.max_duration_seconds)


def words_per_minute(lines: list[VoiceLine]) -> float | None:
    seconds = sum(line.seconds for line in lines)
    words = sum(len(line.text.split()) for line in lines)
    return words * 60.0 / seconds if seconds > 0 and words else None


def speaking_rate(inputs: ScoreInputs) -> ScoreItem | None:
    quality = inputs.settings.quality
    results = []
    for language, voices in inputs.voices.items():
        rate = words_per_minute([line for key, line in voices.items() if key.startswith("scene-")])
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
