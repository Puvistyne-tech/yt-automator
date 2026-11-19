from __future__ import annotations

from typing import Any

import pytest

from autotube.infrastructure.providers.tts.kokoro_voice import KokoroOptions
from autotube.infrastructure.providers.tts.mlx_audio_presets import default_presets
from autotube.pipelines.narrated_video.settings.narrator_voices import (
    NARRATOR_VOICE_TITLES,
    PROVIDER_DEFAULT_VOICE,
)
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings

SCHEMA = KidsStorySettings.model_json_schema()
LANGUAGES = ["en", "ta"]


def definition(node: dict[str, Any]) -> dict[str, Any]:
    reference = node.get("$ref")
    if reference is None:
        return node
    found: dict[str, Any] = SCHEMA["$defs"][reference.rsplit("/", 1)[-1]]
    return found


def language_schema(language: str) -> dict[str, Any]:
    voice = definition(SCHEMA["properties"]["voice"])
    narrator = definition(voice["properties"]["narrator_voice"])
    found: dict[str, Any] = narrator["properties"][language]
    return found


def offered(language: str) -> list[str]:
    return [option["const"] for option in language_schema(language)["oneOf"]]


@pytest.mark.parametrize("language", LANGUAGES)
def test_each_language_offers_titled_voices_with_the_provider_default_first(
    language: str,
) -> None:
    schema = language_schema(language)
    assert schema["type"] == "string"
    assert schema["default"] == PROVIDER_DEFAULT_VOICE
    assert offered(language) == list(NARRATOR_VOICE_TITLES[language])
    assert offered(language)[0] == PROVIDER_DEFAULT_VOICE
    assert all(option["title"] for option in schema["oneOf"])


def test_the_provider_default_option_is_labelled_for_people() -> None:
    assert NARRATOR_VOICE_TITLES["en"][""] == "Default for the provider"
    assert NARRATOR_VOICE_TITLES["ta"]["kayal"] == "Kayal, Tamil female (Maya 2)"


def test_a_stored_voice_outside_the_choices_is_kept() -> None:
    settings = KidsStorySettings.model_validate(
        {"voice": {"narrator_voice": {"en": "my_cloned_voice", "ta": ""}}}
    )
    assert settings.voice.narrator_voice.for_language("en") == "my_cloned_voice"
    assert settings.voice.narrator_voice.for_language("ta") == ""


def test_defaults_leave_the_voice_to_the_provider() -> None:
    narrator = KidsStorySettings().voice.narrator_voice
    assert [narrator.for_language(language) for language in LANGUAGES] == ["", ""]


def test_every_mlx_audio_preset_is_offered_in_each_language_it_speaks() -> None:
    missing = [
        (preset_id, language)
        for preset_id, preset in default_presets().items()
        for language in preset.languages
        if preset_id not in NARRATOR_VOICE_TITLES[language]
    ]
    assert missing == []


def test_every_other_english_choice_is_a_voice_kokoro_knows() -> None:
    others = set(NARRATOR_VOICE_TITLES["en"]) - set(default_presets()) - {""}
    assert others
    assert others <= set(KokoroOptions().voices)


def test_tamil_offers_only_mlx_audio_presets() -> None:
    assert set(NARRATOR_VOICE_TITLES["ta"]) - {""} <= set(default_presets())
