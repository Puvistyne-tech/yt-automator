from __future__ import annotations

from typing import Any

from autotube.pipelines.narrated_video.settings.look_choices import CUSTOM_STYLE

LEGACY_ART_STYLE = (
    "soft watercolor picture-book illustration for young children, warm pastel colours, "
    "rounded friendly shapes, gentle golden light, clean uncluttered composition"
)
LEGACY_NEGATIVE_PROMPT = (
    "text, letters, words, captions, watermark, logo, signature, scary, dark, gloomy, "
    "violence, weapons, sharp teeth, realistic photo, distorted faces, extra limbs"
)
ART_STYLE_KEY = "art_style"
NEGATIVE_PROMPT_KEY = "negative_prompt"
LEGACY_KEYS = frozenset({ART_STYLE_KEY, NEGATIVE_PROMPT_KEY})
KEPT_MOTION_AND_LETTERING = {"use_style_motion": False, "use_style_lettering": False}


def usable_text(value: object, fallback: str, allow_blank: bool) -> str:
    if not isinstance(value, str) or (not allow_blank and not value.strip()):
        return fallback
    return value


def legacy_look(art_style: str, negative_prompt: str) -> dict[str, Any]:
    if (art_style, negative_prompt) == (LEGACY_ART_STYLE, LEGACY_NEGATIVE_PROMPT):
        return dict(KEPT_MOTION_AND_LETTERING)
    custom = {"prompt": art_style, "negative_prompt": negative_prompt}
    return {**KEPT_MOTION_AND_LETTERING, "visual_style": CUSTOM_STYLE, "custom_style": custom}


def migrated_look(data: object) -> object:
    if not isinstance(data, dict):
        return data
    series = data.get("series")
    if not isinstance(series, dict) or not LEGACY_KEYS & series.keys():
        return data
    kept = {key: value for key, value in series.items() if key not in LEGACY_KEYS}
    migrated = {**data, "series": kept}
    if "look" not in data:
        art_style = usable_text(series.get(ART_STYLE_KEY), LEGACY_ART_STYLE, allow_blank=False)
        negative = usable_text(
            series.get(NEGATIVE_PROMPT_KEY), LEGACY_NEGATIVE_PROMPT, allow_blank=True
        )
        migrated["look"] = legacy_look(art_style, negative)
    return migrated
