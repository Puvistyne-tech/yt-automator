from __future__ import annotations

from pydantic import Field, field_validator

from autotube.domain.video_look import SubtitlePosition
from autotube.pipelines.narrated_video.settings.base import HexColor, SettingsSection, color
from autotube.pipelines.narrated_video.settings.choices import SUBTITLE_POSITION_CHOICES

PROVIDER_OUTLINE = -1.0


class SubtitleLookSettings(SettingsSection):
    karaoke: bool = Field(
        default=False,
        title="Karaoke highlight",
        description="Colour each word in the highlight colour while the narrator says it, using "
        "the narration's word timings. Only burned-in subtitles can show it.",
    )
    position: SubtitlePosition = Field(
        default=SubtitlePosition.BOTTOM,
        json_schema_extra=SUBTITLE_POSITION_CHOICES,
        title="Position",
        description="Where burned-in subtitles sit. The bottom margin is kept from the bottom "
        "edge, or from the top edge when they sit at the top; the middle ignores it.",
    )
    bold: bool = Field(
        default=False, title="Bold", description="Draw burned-in subtitles in bold letters."
    )
    shadow: float = Field(
        default=0.0,
        ge=0,
        le=20,
        title="Shadow",
        description="Distance in pixels of a dark drop shadow behind the letters; 0 is none.",
    )
    outline_width: float = Field(
        default=PROVIDER_OUTLINE,
        ge=PROVIDER_OUTLINE,
        le=20,
        title="Outline width",
        description="Outline thickness in pixels, or the box padding when the box is on. "
        "-1 keeps the media provider's subtitle outline setting; 0 draws none.",
    )
    box_background: bool = Field(
        default=False,
        title="Box behind the text",
        description="Draw a filled box behind each subtitle instead of an outline round the "
        "letters.",
    )
    box_color: HexColor = color("#000000", "Box colour", "Colour of the box behind the text.")
    box_opacity: float = Field(
        default=0.6,
        ge=0,
        le=1,
        title="Box opacity",
        description="How solid the box is: 0 is see-through, 1 is fully solid.",
    )

    @field_validator("outline_width")
    @classmethod
    def check_outline_width(cls, value: float) -> float:
        if value != PROVIDER_OUTLINE and value < 0:
            raise ValueError("subtitles.outline_width must be -1 or from 0 to 20")
        return value

    def outline_override(self) -> float | None:
        return None if self.outline_width == PROVIDER_OUTLINE else self.outline_width
