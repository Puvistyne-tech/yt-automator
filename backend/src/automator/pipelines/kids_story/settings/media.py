from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from automator.domain.capabilities import CameraMove
from automator.pipelines.kids_story.settings.base import (
    LocalizedText,
    SettingsSection,
    localized_text,
)


class ShortArtMode(StrEnum):
    NATIVE = "native"
    CROP = "crop"


class Corner(StrEnum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class VisualSettings(SettingsSection):
    image_candidates: int = Field(
        default=2, ge=1, le=8, title="Pictures per scene", description="Candidates drawn per scene."
    )
    hero_candidates: int = Field(
        default=4,
        ge=1,
        le=8,
        title="Pictures per hero scene",
        description="Candidates drawn for the story's most important scenes.",
    )
    hero_scene_count: int = Field(
        default=2, ge=0, le=5, title="Hero scenes", description="How many scenes count as heroes."
    )
    use_vision_judge: bool = Field(
        default=True,
        title="Let the language model pick pictures",
        description="Ask a vision-capable language model for the best candidate.",
    )
    character_sheets: bool = Field(
        default=True,
        title="Character sheets",
        description="Draw each character once and use it as a reference for every scene.",
    )
    sheet_size: int = Field(
        default=1024, ge=256, le=2048, title="Character sheet size", description="Pixels square."
    )
    base_seed: int = Field(
        default=7, ge=0, title="Seed", description="Base random seed so a run can be redrawn."
    )
    motion_intensity: float = Field(
        default=0.5, ge=0, le=1, title="Motion intensity", description="Camera movement strength."
    )
    hero_motion_intensity: float = Field(
        default=0.7, ge=0, le=1, title="Hero motion intensity", description="For hero scenes."
    )
    card_camera: CameraMove = Field(
        default=CameraMove.PUSH_IN,
        title="Card camera move",
        description="How the camera moves over the intro and outro cards.",
    )
    short_art_mode: ShortArtMode = Field(
        default=ShortArtMode.CROP,
        title="Vertical pictures",
        description="Crop the wide picture for the Short, or draw a new vertical one.",
    )
    crop_focus: float = Field(
        default=0.5,
        ge=0,
        le=1,
        title="Crop focus",
        description="Horizontal position of the vertical crop: 0 is left, 1 is right.",
    )
    overlay_series_badge: bool = Field(
        default=False,
        title="Series badge",
        description="Draw the series name in a corner of every scene picture.",
    )
    badge_corner: Corner = Field(
        default=Corner.TOP_LEFT, title="Badge corner", description="Where the badge goes."
    )
    badge_size_ratio: float = Field(
        default=0.045,
        gt=0,
        le=0.2,
        title="Badge text size",
        description="Badge text height as a share of the picture height.",
    )


class VoiceSettings(SettingsSection):
    narrator_voice: LocalizedText = localized_text(
        "", "", "Narrator voice", "Voice id per language. Empty uses the provider's default."
    )
    speed: float = Field(
        default=0.95, ge=0.5, le=1.5, title="Speaking speed", description="1 is normal speed."
    )
    include_intro: bool = Field(
        default=True, title="Speak the intro line", description="Narrate the series intro line."
    )
    include_outro: bool = Field(
        default=True, title="Speak the outro line", description="Narrate the series outro line."
    )


class MusicSettings(SettingsSection):
    enabled: bool = Field(default=True, title="Background music", description="Add a music bed.")
    mood_prompt: str = Field(
        default="gentle playful lullaby with soft marimba, ukulele and light flute, calm and warm",
        min_length=1,
        title="Music mood",
        description="Describes the music to the music model.",
    )
    volume: float = Field(
        default=0.18, ge=0, le=1, title="Music volume", description="Volume of the bed."
    )
    ducking: float = Field(
        default=0.6,
        ge=0,
        le=1,
        title="Ducking",
        description="How much the music dips while the narrator speaks.",
    )


class SoundEffectSettings(SettingsSection):
    enabled: bool = Field(
        default=True, title="Sound effects", description="Add the story's sound effect cues."
    )
    prompt_template: str = Field(
        default="soft cartoon sound effect for a children's story: {cue}",
        min_length=1,
        title="Sound effect prompt",
        description="Prompt per cue. {cue} is replaced by the cue.",
    )
    duration_seconds: float = Field(
        default=1.5, gt=0, le=10, title="Effect length", description="Seconds per effect."
    )
    volume: float = Field(default=0.5, ge=0, le=2, title="Effect volume", description="Loudness.")
    offset_seconds: float = Field(
        default=0.3, ge=0, le=10, title="Effect delay", description="Seconds into the scene."
    )
