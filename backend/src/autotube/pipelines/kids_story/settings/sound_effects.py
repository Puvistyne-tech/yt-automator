from __future__ import annotations

from pydantic import Field

from autotube.pipelines.kids_story.settings.base import SettingsSection


class SoundEffectSettings(SettingsSection):
    enabled: bool = Field(
        default=True, title="Sound effects", description="Add the story's sound effect cues."
    )
    max_per_scene: int = Field(
        default=2,
        ge=0,
        le=5,
        title="Most effects per scene",
        description="How many sound cues the writer may give each scene. Extra cues are dropped.",
    )
    prompt_template: str = Field(
        default="soft cartoon sound effect for a children's story: {cue}",
        min_length=1,
        title="Sound effect prompt",
        description="Prompt per cue. {cue} is replaced by the cue.",
    )
    duration_seconds: float = Field(
        default=1.5,
        gt=0,
        le=10,
        title="Effect length",
        description="How many seconds each sound effect lasts.",
    )
    volume: float = Field(
        default=0.5,
        ge=0,
        le=2,
        title="Effect volume",
        description="Loudness of each sound effect: 1 is unchanged, 2 is twice as loud.",
    )
    offset_seconds: float = Field(
        default=0.3,
        ge=0,
        le=10,
        title="Effect delay",
        description="Seconds after a scene starts before its sound effect plays.",
    )
