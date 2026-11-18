from __future__ import annotations

from pathlib import Path

from pydantic import Field

from automator.domain.capabilities import Capability, MusicRequest
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.music.music_box import MusicBoxTuning, render_music_box
from automator.infrastructure.providers.seeds import prompt_seed
from automator.infrastructure.providers.spec import ProviderOptions, ProviderSpec
from automator.infrastructure.providers.wav_io import write_wav


class SynthMusicOptions(ProviderOptions):
    tempo_bpm: float = Field(
        default=72.0, ge=30, le=180, title="Tempo", description="Beats per minute."
    )
    volume: float = Field(
        default=0.6, gt=0.0, le=1.0, title="Peak level", description="Peak sample level."
    )
    fade_seconds: float = Field(
        default=2.0, ge=0.0, title="Fade", description="Fade in and fade out length in seconds."
    )
    pad_level: float = Field(
        default=0.5, ge=0.0, le=1.0, title="Pad level", description="Loudness of the soft chords."
    )
    chime_level: float = Field(
        default=0.8, ge=0.0, le=1.0, title="Chime level", description="Loudness of the melody."
    )
    note_density: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
        title="Note density",
        description="Chance that each eighth note plays a chime.",
    )
    sample_rate: int = Field(
        default=44100, ge=8000, le=96000, title="Sample rate", description="Output rate in Hz."
    )


class SynthMusic:
    provider_id = "synth_music"

    def __init__(self, options: SynthMusicOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        return None

    def tuning(self) -> MusicBoxTuning:
        return MusicBoxTuning(
            sample_rate=self.options.sample_rate,
            tempo_bpm=self.options.tempo_bpm,
            volume=self.options.volume,
            fade_seconds=self.options.fade_seconds,
            pad_level=self.options.pad_level,
            chime_level=self.options.chime_level,
            note_density=self.options.note_density,
        )

    def compose(self, request: MusicRequest, output: Path) -> Path:
        samples = render_music_box(
            prompt_seed(request.prompt), request.duration_seconds, self.tuning()
        )
        return write_wav(output, samples, self.options.sample_rate)


SPEC = ProviderSpec(
    provider_id=SynthMusic.provider_id,
    capability=Capability.MUSIC,
    name="Music box synth",
    description="A gentle generated music-box and pad loop. Always available.",
    options=SynthMusicOptions,
    factory=SynthMusic,
    offline=True,
)
