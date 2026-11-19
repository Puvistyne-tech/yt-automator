from __future__ import annotations

from typing import Any

from pydantic import Field

from autotube.pipelines.narrated_video.settings.base import LocalizedText
from autotube.pipelines.narrated_video.settings.choices import titled_choices

PROVIDER_DEFAULT_VOICE = ""
PROVIDER_DEFAULT_TITLE = "Default for the provider"

NARRATOR_VOICE_TITLES: dict[str, dict[str, str]] = {
    "en": {
        PROVIDER_DEFAULT_VOICE: PROVIDER_DEFAULT_TITLE,
        "warm_storyteller": "Warm storyteller (Qwen3-TTS)",
        "qwen3_narrator": "Ryan, playful narrator (Qwen3-TTS)",
        "news_reader": "News reader (Chatterbox)",
        "af_heart": "Heart, American female (Kokoro)",
        "af_bella": "Bella, American female (Kokoro)",
        "af_nicole": "Nicole, American female (Kokoro)",
        "am_michael": "Michael, American male (Kokoro)",
        "am_fenrir": "Fenrir, American male (Kokoro)",
        "bf_emma": "Emma, British female (Kokoro)",
        "bm_george": "George, British male (Kokoro)",
    },
    "ta": {
        PROVIDER_DEFAULT_VOICE: PROVIDER_DEFAULT_TITLE,
        "kayal": "Kayal, Tamil female (Maya 2)",
        "vaidehi": "Vaidehi, Tamil female (Maya 2)",
        "svara_male": "Svara, Tamil male (Svara TTS)",
    },
}


def voice_choice(language: str, title: str, description: str) -> Any:
    return Field(
        default=PROVIDER_DEFAULT_VOICE,
        title=title,
        description=description,
        json_schema_extra=titled_choices(NARRATOR_VOICE_TITLES[language]),
    )


class LocalizedVoice(LocalizedText):
    en: str = voice_choice("en", "English", "Narrator voice for English videos.")
    ta: str = voice_choice("ta", "Tamil", "Narrator voice for Tamil videos.")
