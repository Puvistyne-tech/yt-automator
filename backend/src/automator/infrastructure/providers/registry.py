from __future__ import annotations

from typing import Any

from automator.domain.capabilities import Capability
from automator.infrastructure.providers.image import mflux, offline_image
from automator.infrastructure.providers.llm import gemini, groq, offline_text, ollama
from automator.infrastructure.providers.media import ffmpeg_media
from automator.infrastructure.providers.motion import depthflow, ffmpeg_pan_zoom
from automator.infrastructure.providers.music import ace_step, library_music, synth_music
from automator.infrastructure.providers.spec import ProviderSpec
from automator.infrastructure.providers.tts import edge_voice, espeak, kokoro_voice, offline_speech

AnySpec = ProviderSpec[Any, Any]

ALL_SPECS: tuple[AnySpec, ...] = (
    groq.SPEC,
    gemini.SPEC,
    ollama.SPEC,
    offline_text.SPEC,
    mflux.SPEC,
    offline_image.SPEC,
    depthflow.SPEC,
    ffmpeg_pan_zoom.SPEC,
    edge_voice.SPEC,
    kokoro_voice.SPEC,
    espeak.SPEC,
    offline_speech.SPEC,
    ace_step.SPEC,
    library_music.SPEC,
    synth_music.SPEC,
    ffmpeg_media.SPEC,
)


def default_order(capability: Capability, specs: tuple[AnySpec, ...] = ALL_SPECS) -> list[str]:
    return [spec.provider_id for spec in specs if spec.capability is capability]
