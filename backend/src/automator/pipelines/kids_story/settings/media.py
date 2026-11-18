from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from automator.domain.capabilities import CameraMove
from automator.pipelines.kids_story.settings.base import (
    Corner,
    LocalizedText,
    Placement,
    SettingsSection,
    localized_text,
)
from automator.pipelines.kids_story.settings.choices import (
    CAMERA_MOVE_CHOICES,
    CORNER_CHOICES,
    SHORT_ART_CHOICES,
)


class ShortArtMode(StrEnum):
    NATIVE = "native"
    CROP = "crop"


class VisualSettings(SettingsSection):
    image_candidates: int = Field(
        default=2,
        ge=1,
        le=8,
        title="Pictures per scene",
        description="How many pictures are drawn for an ordinary scene before the best is kept.",
    )
    hero_candidates: int = Field(
        default=4,
        ge=1,
        le=8,
        title="Pictures per hero scene",
        description="Candidates drawn for the story's most important scenes.",
    )
    hero_scene_count: int = Field(
        default=2,
        ge=0,
        le=5,
        title="Hero scenes",
        description="How many of the story's key scenes get extra pictures and livelier motion.",
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
        default=1024,
        ge=256,
        le=2048,
        title="Character sheet size",
        description="Width and height in pixels of each square character reference picture.",
    )
    base_seed: int = Field(
        default=7, ge=0, title="Seed", description="Base random seed so a run can be redrawn."
    )
    motion_intensity: float = Field(
        default=0.5,
        ge=0,
        le=1,
        title="Motion intensity",
        description="How strongly the camera moves over ordinary scenes: 0 is still, 1 is lively.",
    )
    hero_motion_intensity: float = Field(
        default=0.7,
        ge=0,
        le=1,
        title="Hero motion intensity",
        description="How strongly the camera moves over hero scenes: 0 is still, 1 is lively.",
    )
    card_camera: CameraMove = Field(
        default=CameraMove.PUSH_IN,
        json_schema_extra=CAMERA_MOVE_CHOICES,
        title="Card camera move",
        description="How the camera moves over the intro and outro cards.",
    )
    short_art_mode: ShortArtMode = Field(
        default=ShortArtMode.CROP,
        json_schema_extra=SHORT_ART_CHOICES,
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
        title="Brand mark",
        description="Draw the brand mark in a corner of every episode and Short scene picture.",
    )
    badge_text: str = Field(
        default="",
        max_length=40,
        title="Brand mark text",
        description="The brand mark shown in the corner of every picture. Empty means no mark.",
    )
    badge_corner: Corner = Field(
        default=Placement.TOP_LEFT,
        json_schema_extra=CORNER_CHOICES,
        title="Brand mark corner",
        description="The corner of the picture where the brand mark is drawn.",
    )
    badge_size_ratio: float = Field(
        default=0.045,
        gt=0,
        le=0.2,
        title="Brand mark size",
        description="Brand mark letter height as a share of the picture height.",
    )


class VoiceSettings(SettingsSection):
    narrator_voice: LocalizedText = localized_text(
        "", "", "Narrator voice", "Voice id per language. Empty uses the provider's default."
    )
    speed: float = Field(
        default=0.95,
        ge=0.5,
        le=1.5,
        title="Speaking speed",
        description="How fast the narrator speaks: 1 is normal, lower is slower.",
    )
    include_intro: bool = Field(
        default=True, title="Speak the intro line", description="Narrate the series intro line."
    )
    include_outro: bool = Field(
        default=True, title="Speak the outro line", description="Narrate the series outro line."
    )


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
