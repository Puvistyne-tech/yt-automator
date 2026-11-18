from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field

from autotube.domain.capabilities import Capability, Speech, SpeechRequest
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.host import first_reason
from autotube.infrastructure.providers.output_path import ensure_parent
from autotube.infrastructure.providers.spec import ProviderOptions, ProviderSpec
from autotube.infrastructure.providers.tts import mlx_audio_worker
from autotube.infrastructure.providers.tts.mlx_audio_presets import (
    VoicePreset,
    choose_preset,
    default_presets,
)
from autotube.infrastructure.providers.tts.speech_text import require_text
from autotube.infrastructure.providers.tts.whisper_aligner import (
    AlignmentOptions,
    WhisperAligner,
    WordAligner,
    estimated_speech,
)
from autotube.infrastructure.providers.wav_io import wav_duration

WORKER_SCRIPT = Path(mlx_audio_worker.__file__)


class MlxAudioOptions(ProviderOptions):
    python: str = Field(
        default="/Users/styne/Documents/DEV/yt/kutty/bakeoff/.venv/bin/python",
        title="mlx-audio Python",
        description="Python of a separate venv with mlx-audio installed.",
    )
    models_root: str = Field(
        default="/Volumes/backup/bakeoff-models/local",
        title="Models folder",
        description="Folder holding one subfolder per mlx-audio model.",
    )
    hf_home: str = Field(
        default="/Volumes/backup/bakeoff-models/hf",
        title="Hugging Face cache",
        description="HF_HOME for the model process, which runs with the hub offline.",
    )
    timeout_seconds: float = Field(
        default=900.0, gt=0, title="Timeout", description="Seconds allowed per narration."
    )
    default_voice: dict[str, str] = Field(
        default_factory=lambda: {"en": "warm_storyteller", "ta": "kayal"},
        title="Default voice by language",
        description="Voice preset used for each language when the request names none.",
    )
    presets: dict[str, VoicePreset] = Field(
        default_factory=default_presets,
        title="Voice presets",
        description="Named voices: a model folder, its languages and its generation arguments.",
    )
    alignment: AlignmentOptions = Field(
        default_factory=AlignmentOptions,
        title="Alignment",
        description="Whisper alignment of the estimated word timings.",
    )


def worker_job(preset: VoicePreset, request: SpeechRequest, models_root: str, output: Path) -> str:
    job = {
        "model_dir": str(Path(models_root) / preset.model),
        "text": request.text,
        "kwargs": preset.kwargs,
        "sentence_split": preset.sentence_split,
        "pause_ms": preset.pause_ms,
        "output": str(output),
    }
    return json.dumps(job, ensure_ascii=False)


class MlxAudioSpeech:
    provider_id = "mlx_audio"

    def __init__(
        self,
        options: MlxAudioOptions,
        context: ProviderContext,
        aligner: WordAligner | None = None,
    ) -> None:
        self.options = options
        self.context = context
        self.aligner = aligner or WhisperAligner(context.host, options.alignment)

    def available(self) -> str | None:
        host = self.context.host
        return first_reason(
            host.missing_path(self.options.python, "mlx-audio Python"),
            host.missing_path(self.options.models_root, "mlx-audio models folder"),
        )

    def synthesize(self, request: SpeechRequest, output: Path) -> Speech:
        require_text(self.provider_id, request)
        preset = choose_preset(self.options.presets, self.options.default_voice, request)
        ensure_parent(output)
        self.context.runner.run(
            [self.options.python, "-I", str(WORKER_SCRIPT)],
            self.options.timeout_seconds,
            stdin=worker_job(preset, request, self.options.models_root, output),
            env={"HF_HOME": self.options.hf_home, "HF_HUB_OFFLINE": "1"},
        )
        duration = wav_duration(output)
        return estimated_speech(output, duration, request, self.aligner, self.options.alignment)


SPEC = ProviderSpec(
    provider_id=MlxAudioSpeech.provider_id,
    capability=Capability.TTS,
    name="mlx-audio voices (local)",
    description="Expressive local voices on Apple silicon, run in their own Python environment.",
    options=MlxAudioOptions,
    factory=MlxAudioSpeech,
    offline=True,
)
