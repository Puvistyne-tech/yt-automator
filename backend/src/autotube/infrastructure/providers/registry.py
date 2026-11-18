from __future__ import annotations

from typing import Any

from autotube.domain.capabilities import Capability
from autotube.infrastructure.providers.image import mflux, offline_image
from autotube.infrastructure.providers.llm import gemini, groq, offline_text, ollama
from autotube.infrastructure.providers.media import ffmpeg_media
from autotube.infrastructure.providers.motion import depthflow, ffmpeg_pan_zoom
from autotube.infrastructure.providers.music import ace_step, library_music, synth_music
from autotube.infrastructure.providers.spec import ProviderSpec
from autotube.infrastructure.providers.tts import (
    edge_voice,
    espeak,
    kokoro_voice,
    mlx_audio_voice,
    offline_speech,
)

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
    mlx_audio_voice.SPEC,
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
