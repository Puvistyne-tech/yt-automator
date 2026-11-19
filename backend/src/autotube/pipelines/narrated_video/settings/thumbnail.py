from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from autotube.pipelines.narrated_video.settings.base import (
    Edge,
    HexColor,
    LocalizedList,
    LocalizedText,
    Placement,
    SettingsSection,
    color,
    localized_list,
    localized_text,
)
from autotube.pipelines.narrated_video.settings.choices import EDGE_CHOICES
from autotube.pipelines.narrated_video.settings.placeholders import (
    THUMBNAIL_PLACEHOLDERS,
    checked_template,
)

LATIN_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
STYLE_LETTERING_NOTE = "Used when Letter in the style's colours is off, or for a custom style."
TAMIL_FONTS = [
    "/System/Library/Fonts/Supplemental/Tamil Sangam MN.ttc",
    "/System/Library/Fonts/Supplemental/Tamil MN.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
]


class ThumbnailSettings(SettingsSection):
    title_text: bool = Field(
        default=True,
        title="Text on thumbnail",
        description="Draw the thumbnail text on every thumbnail.",
    )
    text_template: LocalizedText = localized_text(
        "{title}",
        "{title}",
        "Thumbnail text",
        "Text drawn on the thumbnail per language, one line per row; {title} {series} {moral} "
        "and {hook} are filled in.",
    )
    candidates: int = Field(
        default=1,
        ge=1,
        le=8,
        title="Thumbnail pictures to choose from",
        description="How many thumbnail pictures are drawn; with more than one, the picture "
        "judge keeps the best when Let the language model pick pictures is on, otherwise "
        "the first.",
    )
    width: int = Field(
        default=1280,
        ge=320,
        le=3840,
        title="Width",
        description="Width of the episode thumbnail in pixels.",
    )
    height: int = Field(
        default=720,
        ge=180,
        le=2160,
        title="Height",
        description="Height of every thumbnail in pixels.",
    )
    max_bytes: int = Field(
        default=2_000_000,
        ge=100_000,
        le=2_000_000,
        title="Largest thumbnail file",
        description="Thumbnails are saved as JPEG at lower quality until they fit in this size.",
    )
    jpeg_quality: int = Field(
        default=92,
        ge=40,
        le=100,
        title="Thumbnail quality",
        description="JPEG quality tried first; lower quality is used only to meet the size limit.",
    )
    min_jpeg_quality: int = Field(
        default=40,
        ge=10,
        le=100,
        title="Lowest thumbnail quality",
        description="The JPEG quality is never lowered below this to meet the size limit.",
    )
    downscale_step: float = Field(
        default=0.85,
        ge=0.5,
        lt=1,
        title="Thumbnail shrink step",
        description="When the lowest quality is still too large, the width is multiplied by this.",
    )
    min_width: int = Field(
        default=640,
        ge=160,
        le=3840,
        title="Narrowest thumbnail",
        description="Thumbnails are never shrunk below this width in pixels to fit the size limit.",
    )
    text_position: Edge = Field(
        default=Placement.BOTTOM,
        json_schema_extra=EDGE_CHOICES,
        title="Title position",
        description="Draw the title along the top or the bottom of the thumbnail.",
    )
    text_size_ratio: float = Field(
        default=0.11,
        gt=0,
        le=0.4,
        title="Title size",
        description="Letter height as a share of the thumbnail height.",
    )
    margin_ratio: float = Field(
        default=0.05,
        ge=0,
        le=0.3,
        title="Title margin",
        description="Space between the lettering and the edge, as a share of the height.",
    )
    outline_ratio: float = Field(
        default=0.08,
        ge=0,
        le=0.5,
        title="Outline thickness",
        description="Outline width as a share of the letter height.",
    )
    text_color: HexColor = color(
        "#FFFFFF",
        "Title colour",
        f"Colour of the letters on thumbnails and cards. {STYLE_LETTERING_NOTE}",
    )
    outline_color: HexColor = color(
        "#3A2A1A",
        "Title outline",
        f"Colour around the letters on thumbnails and cards. {STYLE_LETTERING_NOTE}",
    )
    font_files: LocalizedList = localized_list(
        LATIN_FONTS,
        TAMIL_FONTS,
        "Font files",
        "Font files tried in order for every lettered picture; the first one found is used.",
        machine_local=True,
    )

    @field_validator("text_template")
    @classmethod
    def check_text_template(cls, value: LocalizedText) -> LocalizedText:
        return checked_template("thumbnail.text_template", value, THUMBNAIL_PLACEHOLDERS)

    @model_validator(mode="after")
    def check_quality_range(self) -> ThumbnailSettings:
        if self.min_jpeg_quality > self.jpeg_quality:
            raise ValueError("lowest thumbnail quality must not exceed thumbnail quality")
        return self
