from __future__ import annotations

from collections.abc import Iterable

from pydantic import Field

from autotube.domain.capabilities import CameraMove
from autotube.domain.image_style import HexColour, ImageStyleHints, Outline, Texture
from autotube.domain.model_base import DomainModel
from autotube.pipelines.narrated_video.settings.look import LookSettings
from autotube.pipelines.narrated_video.settings.look_choices import CUSTOM_STYLE
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.styles.colour_names import colour_words
from autotube.pipelines.narrated_video.styles.library import (
    StyleBase,
    StyleLettering,
    VisualStyle,
    style_named,
)
from autotube.pipelines.narrated_video.styles.modifiers import ColourMood, Lighting
from autotube.pipelines.narrated_video.styles.palette_mood import mood_palette
from autotube.pipelines.narrated_video.styles.style_prompt import modifier_prompts

CUSTOM_TITLE = "Custom style"
MOTION_WORDING = {"prompt", "negative_prompt"}


class ResolvedMotion(DomainModel):
    intensity: float = Field(ge=0, le=1)
    hero_intensity: float = Field(ge=0, le=1)
    card_camera: CameraMove
    held_frame_rate: int | None = None
    feel: str = ""


class ResolvedStyle(DomainModel):
    style_id: str
    title: str
    prompt: str
    negative_prompt: str
    palette: tuple[HexColour, ...]
    outline: Outline
    texture: Texture
    motion: ResolvedMotion
    motion_prompt: str = ""
    motion_negative_prompt: str = ""
    lettering: StyleLettering

    night: bool = False

    def hints(self, scene_text: str = "") -> ImageStyleHints:
        return ImageStyleHints(
            palette=self.palette,
            outline=self.outline,
            texture=self.texture,
            night=self.night,
            scene_text=scene_text,
        )


def joined_text(parts: Iterable[str]) -> str:
    return ", ".join(part.strip() for part in parts if part.strip())


def joined_terms(parts: Iterable[str]) -> str:
    seen: dict[str, str] = {}
    for part in parts:
        for term in part.split(","):
            if term.strip():
                seen.setdefault(term.strip().casefold(), term.strip())
    return ", ".join(seen.values())


def chosen_style(look: LookSettings) -> VisualStyle | None:
    if look.visual_style == CUSTOM_STYLE:
        return None
    return style_named(look.visual_style)


def custom_base(look: LookSettings) -> StyleBase:
    custom = look.custom_style
    return StyleBase(
        id=CUSTOM_STYLE,
        title=CUSTOM_TITLE,
        prompt=joined_text([custom.prompt, f"main colours {colour_words(custom.palette)}"]),
        negative_prompt=custom.negative_prompt,
        palette=tuple(custom.palette),
        outline=custom.outline,
        texture=custom.texture,
    )


def settings_motion(settings: KidsStorySettings) -> ResolvedMotion:
    visuals = settings.visuals
    return ResolvedMotion(
        intensity=visuals.motion_intensity,
        hero_intensity=visuals.hero_motion_intensity,
        card_camera=visuals.card_camera,
    )


def resolved_motion(settings: KidsStorySettings, style: VisualStyle | None) -> ResolvedMotion:
    if style is None or not settings.look.use_style_motion:
        return settings_motion(settings)
    return ResolvedMotion.model_validate(style.motion.model_dump(exclude=MOTION_WORDING))


def resolved_lettering(settings: KidsStorySettings, style: VisualStyle | None) -> StyleLettering:
    if style is None or not settings.look.use_style_lettering:
        thumbnail = settings.thumbnail
        return StyleLettering(text=thumbnail.text_color, outline=thumbnail.outline_color)
    return style.lettering


def motion_negative(look: LookSettings, style: VisualStyle | None) -> str:
    return style.motion.negative_prompt if style else look.custom_style.motion_negative_prompt


def resolve_style(settings: KidsStorySettings) -> ResolvedStyle:
    look = settings.look
    style = chosen_style(look)
    base: StyleBase = style or custom_base(look)
    return ResolvedStyle(
        style_id=base.id,
        title=base.title,
        prompt=joined_text([base.prompt, *modifier_prompts(look), look.extra_prompt]),
        negative_prompt=joined_terms(
            [settings.safety.picture_exclusions, base.negative_prompt, look.extra_negative_prompt]
        ),
        palette=mood_palette(base.palette, look.colour_mood, look.mood_palette),
        outline=base.outline,
        texture=base.texture,
        motion=resolved_motion(settings, style),
        motion_prompt=style.motion.prompt if style else look.custom_style.motion_prompt,
        motion_negative_prompt=motion_negative(look, style),
        lettering=resolved_lettering(settings, style),
        night=asks_for_night(look),
    )


def asks_for_night(look: LookSettings) -> bool:
    return look.lighting is Lighting.MOONLIGHT or look.colour_mood is ColourMood.NIGHT
