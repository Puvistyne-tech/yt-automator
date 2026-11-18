from __future__ import annotations

from pydantic import Field, field_validator

from autotube.pipelines.kids_story.settings.base import (
    LocalizedNumber,
    LocalizedText,
    SettingsSection,
    localized_text,
)

DEFAULT_SPEED = 0.95


def speed_field(title: str, description: str) -> float:
    found: float = Field(
        default=DEFAULT_SPEED, ge=0.5, le=1.5, title=title, description=description
    )
    return found


class LocalizedSpeed(LocalizedNumber):
    en: float = speed_field("English", "Speaking speed for English videos.")
    ta: float = speed_field("Tamil", "Speaking speed for Tamil videos.")


def speed_for_every_language(value: object) -> object:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return value
    return dict.fromkeys(LocalizedSpeed.model_fields, value)


class VoiceSettings(SettingsSection):
    narrator_voice: LocalizedText = localized_text(
        "", "", "Narrator voice", "Voice id per language. Empty uses the provider's default."
    )
    speed: LocalizedSpeed = Field(
        default_factory=LocalizedSpeed,
        title="Speaking speed",
        description="How fast the narrator speaks in each language: 1 is normal, lower is slower.",
    )
    include_intro: bool = Field(
        default=True, title="Speak the intro line", description="Narrate the series intro line."
    )
    include_outro: bool = Field(
        default=True, title="Speak the outro line", description="Narrate the series outro line."
    )

    @field_validator("speed", mode="before")
    @classmethod
    def migrate_single_speed(cls, value: object) -> object:
        return speed_for_every_language(value)


class MusicSettings(SettingsSection):
    enabled: bool = Field(
        default=True,
        title="Background music",
        description="Play a soft music bed under every episode and Short.",
    )
    mood_prompt: str = Field(
        default="gentle playful lullaby with soft marimba, ukulele and light flute, calm and warm",
        min_length=1,
        title="Music mood",
        description="Describes the music to the music model.",
    )
    short_mood_prompt: str = Field(
        default="",
        max_length=500,
        title="Short music mood",
        description="Describes the music under the Short. Empty uses the music mood.",
    )
    volume: float = Field(
        default=0.18,
        ge=0,
        le=1,
        title="Music volume",
        description="Loudness of the music bed: 0 is silent, 1 is full volume.",
    )
    ducking: float = Field(
        default=0.6,
        ge=0,
        le=1,
        title="Ducking",
        description="How much the music dips while the narrator speaks.",
    )
