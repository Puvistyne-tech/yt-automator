from __future__ import annotations

from pydantic import Field, JsonValue

from autotube.domain.capabilities import SpeechRequest
from autotube.infrastructure.providers.spec import ProviderOptions
from autotube.infrastructure.providers.tts.voice_language import lookup_language
from autotube.shared.errors import UpstreamFailure

QWEN_DESIGN = "mlx-community__Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit"
QWEN_CUSTOM = "mlx-community__Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit"
MAYA_TAMIL = "aruntemme__maya2-native-mlx-8bit"
STORYTELLER_INSTRUCTION = (
    "A warm, playful storyteller reading a bedtime story to children: gentle and expressive, "
    "a little breathless with excitement on happy lines and soft and slow on sad lines."
)


class VoicePreset(ProviderOptions):
    name: str = Field(title="Name", description="Name shown for this voice.")
    model: str = Field(
        min_length=1,
        title="Model folder",
        description="Folder under the models folder holding the mlx-audio model.",
    )
    languages: list[str] = Field(
        min_length=1, title="Languages", description="Language codes this voice speaks."
    )
    kwargs: dict[str, JsonValue] = Field(
        default_factory=dict,
        title="Generation arguments",
        description="Keyword arguments for the model's generate call, such as voice or instruct.",
    )
    sentence_split: bool = Field(
        default=False,
        title="Split sentences",
        description="Generate each sentence on its own and join them with a pause.",
    )
    pause_ms: int = Field(
        default=0, ge=0, le=5000, title="Pause", description="Milliseconds between sentences."
    )


def default_presets() -> dict[str, VoicePreset]:
    return {
        "warm_storyteller": VoicePreset(
            name="Warm storyteller",
            model=QWEN_DESIGN,
            languages=["en"],
            kwargs={"lang_code": "English", "instruct": STORYTELLER_INSTRUCTION},
        ),
        "qwen3_narrator": VoicePreset(
            name="Qwen3 narrator",
            model=QWEN_CUSTOM,
            languages=["en"],
            kwargs={
                "voice": "Ryan",
                "lang_code": "English",
                "instruct": "Warm, playful storyteller voice for children, expressive.",
            },
        ),
        "news_reader": VoicePreset(
            name="News reader", model="mlx-community__chatterbox-turbo-4bit", languages=["en"]
        ),
        "kayal": VoicePreset(
            name="Kayal", model=MAYA_TAMIL, languages=["ta"], kwargs=tamil_voice("Kayal")
        ),
        "vaidehi": VoicePreset(
            name="Vaidehi", model=MAYA_TAMIL, languages=["ta"], kwargs=tamil_voice("Vaidehi")
        ),
        "svara_male": VoicePreset(
            name="Svara male",
            model="mlx-community__svara-tts-v1-4bit",
            languages=["ta"],
            kwargs={"voice": "Tamil (Male)"},
            sentence_split=True,
            pause_ms=250,
        ),
    }


def tamil_voice(voice: str) -> dict[str, JsonValue]:
    return {"voice": voice, "lang_code": "ta"}


def choose_preset(
    presets: dict[str, VoicePreset], defaults: dict[str, str], request: SpeechRequest
) -> VoicePreset:
    preset_id = request.voice or lookup_language(defaults, request.language)
    if not preset_id:
        raise UpstreamFailure(
            f"mlx_audio has no voice for {request.language!r}", "language_unsupported"
        )
    preset = presets.get(preset_id)
    if preset is None:
        raise UpstreamFailure(f"mlx_audio has no voice preset {preset_id!r}", "voice_unknown")
    if lookup_language(dict.fromkeys(preset.languages, True), request.language) is None:
        raise UpstreamFailure(
            f"mlx_audio voice {preset_id!r} does not speak {request.language!r}",
            "language_unsupported",
        )
    return preset
