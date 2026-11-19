from __future__ import annotations

from enum import StrEnum

STYLE_DEFAULT = "style"


class ColourMood(StrEnum):
    STYLE = STYLE_DEFAULT
    BRIGHT = "bright"
    PASTEL = "pastel"
    WARM = "warm"
    COOL = "cool"
    NIGHT = "night"
    MONOCHROME = "monochrome"
    CUSTOM = "custom"


class Lighting(StrEnum):
    STYLE = STYLE_DEFAULT
    SOFT_DAYLIGHT = "soft_daylight"
    GOLDEN_HOUR = "golden_hour"
    MOONLIGHT = "moonlight"
    STUDIO = "studio"
    DRAMATIC = "dramatic"


class DetailLevel(StrEnum):
    STYLE = STYLE_DEFAULT
    MINIMAL = "minimal"
    BALANCED = "balanced"
    INTRICATE = "intricate"


class BackgroundComplexity(StrEnum):
    STYLE = STYLE_DEFAULT
    PLAIN = "plain"
    SIMPLE = "simple"
    MODERATE = "moderate"
    RICH = "rich"


class Proportions(StrEnum):
    STYLE = STYLE_DEFAULT
    REALISTIC = "realistic"
    CUTE = "cute"


MOOD_PROMPTS: dict[ColourMood, str] = {
    ColourMood.BRIGHT: "bright saturated cheerful colours",
    ColourMood.PASTEL: "soft pale pastel colours",
    ColourMood.WARM: "warm palette of golds, oranges and soft reds",
    ColourMood.COOL: "cool palette of blues, teals and soft greens",
    ColourMood.NIGHT: "calm night-time palette of deep blues with warm glowing lights",
    ColourMood.MONOCHROME: "monochrome palette in shades of a single colour",
    ColourMood.CUSTOM: "colour palette built from these colours: {colours}",
}
LIGHTING_PROMPTS: dict[Lighting, str] = {
    Lighting.SOFT_DAYLIGHT: "soft even daylight",
    Lighting.GOLDEN_HOUR: "warm golden-hour sunlight with long soft shadows",
    Lighting.MOONLIGHT: "gentle silvery moonlight with cosy warm lamps",
    Lighting.STUDIO: "clean bright studio lighting",
    Lighting.DRAMATIC: "dramatic but gentle lighting with soft contrast and glowing highlights",
}
DETAIL_PROMPTS: dict[DetailLevel, str] = {
    DetailLevel.MINIMAL: "minimal detail, simple clear shapes",
    DetailLevel.BALANCED: "moderate detail",
    DetailLevel.INTRICATE: "richly detailed with intricate small touches",
}
BACKGROUND_PROMPTS: dict[BackgroundComplexity, str] = {
    BackgroundComplexity.PLAIN: "plain soft single-colour background",
    BackgroundComplexity.SIMPLE: "simple uncluttered background",
    BackgroundComplexity.MODERATE: "background with some scenery",
    BackgroundComplexity.RICH: "rich detailed background full of scenery",
}
PROPORTION_PROMPTS: dict[Proportions, str] = {
    Proportions.REALISTIC: "natural realistic body proportions",
    Proportions.CUTE: "cute characters with big heads and small rounded bodies",
}
