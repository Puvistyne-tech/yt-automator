from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

HEX_COLOR = r"^#[0-9A-Fa-f]{6}$"
HexColor = Annotated[str, Field(pattern=HEX_COLOR, json_schema_extra={"format": "color"})]


class StoryLanguage(StrEnum):
    ENGLISH = "en"
    TAMIL = "ta"


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
    en: float = Field(default=0.0, ge=0, title="English", description="Value for English.")
    ta: float = Field(default=0.0, ge=0, title="Tamil", description="Value for Tamil.")

    def for_language(self, language: str) -> float:
        value = self.model_dump().get(language)
        return float(value) if isinstance(value, int | float) else self.en


class LocalizedList(SettingsSection):
    en: list[str] = Field(default_factory=list, title="English", description="Items for English.")
    ta: list[str] = Field(default_factory=list, title="Tamil", description="Items for Tamil.")

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


def localized_list(en: list[str], ta: list[str], title: str, description: str) -> Any:
    return Field(
        default_factory=lambda: LocalizedList(en=list(en), ta=list(ta)),
        title=title,
        description=description,
    )


def text_list(items: list[str], title: str, description: str) -> Any:
    return Field(default_factory=lambda: list(items), title=title, description=description)
