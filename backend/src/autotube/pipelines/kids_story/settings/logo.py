from __future__ import annotations

from pathlib import PurePath

from pydantic import Field, field_validator

from autotube.pipelines.kids_story.settings.base import Corner, Placement, SettingsSection
from autotube.pipelines.kids_story.settings.choices import CORNER_CHOICES

LOGO_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")


class LogoSettings(SettingsSection):
    logo_file: str = Field(
        default="",
        max_length=1024,
        title="Logo file",
        description="Full path to a PNG, JPEG or WebP logo on this computer, drawn over the "
        "videos as a watermark. A transparent PNG looks best. Empty means no logo; a path "
        "with no file there fails the run.",
    )
    logo_corner: Corner = Field(
        default=Placement.TOP_RIGHT,
        json_schema_extra=CORNER_CHOICES,
        title="Logo corner",
        description="The corner of the video where the logo sits.",
    )
    logo_size_percent: float = Field(
        default=12.0,
        gt=0,
        le=50,
        title="Logo size",
        description="Logo width as a percentage of the video width.",
    )
    logo_opacity: float = Field(
        default=0.8,
        ge=0,
        le=1,
        title="Logo opacity",
        description="How solid the logo is: 0 is invisible, 1 is fully solid.",
    )
    logo_margin_percent: float = Field(
        default=3.0,
        ge=0,
        le=20,
        title="Logo margin",
        description="Space between the logo and the video edges, as a percentage of the height.",
    )
    logo_on_episode: bool = Field(
        default=True, title="Logo on the episode", description="Draw the logo on the episode."
    )
    logo_on_short: bool = Field(
        default=True, title="Logo on the Short", description="Draw the logo on the Short."
    )

    @field_validator("logo_file")
    @classmethod
    def check_logo_file(cls, value: str) -> str:
        path = value.strip()
        if path and PurePath(path).suffix.lower() not in LOGO_SUFFIXES:
            raise ValueError("visuals.logo_file must be a .png, .jpg, .jpeg or .webp picture")
        return path
