from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator

from autotube.domain.capabilities import CameraMove
from autotube.pipelines.narrated_video.settings.base import (
    Corner,
    Placement,
)
from autotube.pipelines.narrated_video.settings.choices import (
    CAMERA_MOVE_CHOICES,
    CORNER_CHOICES,
    SHORT_ART_CHOICES,
)
from autotube.pipelines.narrated_video.settings.legacy_motion import upgraded_motion_prompt
from autotube.pipelines.narrated_video.settings.logo import LogoSettings
from autotube.pipelines.narrated_video.settings.motion_defaults import MOTION_PROMPT
from autotube.pipelines.narrated_video.text.templates import unknown_placeholders

STYLE_MOTION_NOTE = "Used when Move the way the style suggests is off, or for a custom style."
MOTION_PLACEHOLDERS = frozenset({"action", "visual", "mood"})
JUDGE_CRITERIA = (
    "Pick the picture that best matches the scene, keeps every character on model, "
    "looks warm and safe for small children and has no text in it."
)


class ShortArtMode(StrEnum):
    NATIVE = "native"
    CROP = "crop"


class VisualSettings(LogoSettings):
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
    judge_criteria: str = Field(
        default=JUDGE_CRITERIA,
        min_length=1,
        max_length=1000,
        title="How pictures are picked",
        description="Tells the picture judge what makes the best candidate.",
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
        description="How strongly the camera moves over ordinary scenes: 0 is still, 1 is lively. "
        f"{STYLE_MOTION_NOTE}",
    )
    hero_motion_intensity: float = Field(
        default=0.7,
        ge=0,
        le=1,
        title="Hero motion intensity",
        description="How strongly the camera moves over hero scenes: 0 is still, 1 is lively. "
        f"{STYLE_MOTION_NOTE}",
    )
    motion_prompt: str = Field(
        default=MOTION_PROMPT,
        min_length=1,
        max_length=1000,
        title="Motion prompt",
        description="Describes the animation of each picture. {action} is the scene's one "
        "visible movement (its picture when the script names none), {visual} and {mood} are "
        "the scene's picture and mood.",
    )
    card_camera: CameraMove = Field(
        default=CameraMove.PUSH_IN,
        json_schema_extra=CAMERA_MOVE_CHOICES,
        title="Card camera move",
        description=f"How the camera moves over the intro and outro cards. {STYLE_MOTION_NOTE}",
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

    @field_validator("motion_prompt", mode="before")
    @classmethod
    def upgrade_legacy_motion_prompt(cls, value: object) -> object:
        return upgraded_motion_prompt(value)

    @field_validator("motion_prompt")
    @classmethod
    def check_motion_placeholders(cls, value: str) -> str:
        unknown = unknown_placeholders(value, MOTION_PLACEHOLDERS)
        if unknown:
            names = ", ".join(f"{{{name}}}" for name in unknown)
            raise ValueError(
                f"motion prompt may only use {{action}}, {{visual}} and {{mood}}; unknown: {names}"
            )
        return value
