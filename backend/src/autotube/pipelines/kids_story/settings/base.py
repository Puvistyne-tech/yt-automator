from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from autotube.domain.image_style import HEX_COLOUR_PATTERN
from autotube.domain.ui_schema import MACHINE_LOCAL_KEY

MACHINE_LOCAL: dict[str, JsonValue] = {MACHINE_LOCAL_KEY: True}
HexColor = Annotated[str, Field(pattern=HEX_COLOUR_PATTERN, json_schema_extra={"format": "color"})]


class StoryLanguage(StrEnum):
    ENGLISH = "en"
    TAMIL = "ta"


class Placement(StrEnum):
    TOP = "top"
    BOTTOM = "bottom"
    CENTER = "center"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


Corner = Literal[
    Placement.TOP_LEFT, Placement.TOP_RIGHT, Placement.BOTTOM_LEFT, Placement.BOTTOM_RIGHT
]
Edge = Literal[Placement.TOP, Placement.BOTTOM]


class SettingsSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalizedText(SettingsSection):
    en: str = Field(default="", title="English", description="Text used for English videos.")
    ta: str = Field(
        default="", title="Tamil", description="Text used for Tamil videos, in Tamil script."
    )

    def for_language(self, language: str) -> str:
        value = self.model_dump().get(language)
        return value if isinstance(value, str) else self.en


class LocalizedNumber(SettingsSection):
    en: float = Field(
        default=0.0, ge=0, title="English", description="Value used for English videos."
    )
    ta: float = Field(default=0.0, ge=0, title="Tamil", description="Value used for Tamil videos.")

    def for_language(self, language: str) -> float:
        value = self.model_dump().get(language)
        return float(value) if isinstance(value, int | float) else self.en


class LocalizedList(SettingsSection):
    en: list[str] = Field(
        default_factory=list, title="English", description="Entries used for English videos."
    )
    ta: list[str] = Field(
        default_factory=list, title="Tamil", description="Entries used for Tamil videos."
    )

    def for_language(self, language: str) -> list[str]:
        value = self.model_dump().get(language)
        return [str(item) for item in value] if isinstance(value, list) else list(self.en)


def localized_text(en: str, ta: str, title: str, description: str) -> Any:
    return Field(
        default_factory=lambda: LocalizedText(en=en, ta=ta), title=title, description=description
    )


def localized_number(en: float, ta: float, title: str, description: str) -> Any:
    return Field(
        default_factory=lambda: LocalizedNumber(en=en, ta=ta),
        title=title,
        description=description,
    )


def localized_list(
    en: list[str], ta: list[str], title: str, description: str, machine_local: bool = False
) -> Any:
    return Field(
        default_factory=lambda: LocalizedList(en=list(en), ta=list(ta)),
        title=title,
        description=description,
        json_schema_extra=MACHINE_LOCAL if machine_local else None,
    )


def text_list_field(items: list[str], title: str, description: str) -> Any:
    return Field(default_factory=lambda: list(items), title=title, description=description)


def color(default: str, title: str, description: str) -> Any:
    return Field(default=default, title=title, description=description)
