from __future__ import annotations

from pydantic import Field

from automator.infrastructure.providers.spec import ProviderOptions


class FfmpegOptions(ProviderOptions):
    ffmpeg_binary: str = Field(default="ffmpeg", title="ffmpeg command", description="Encoder.")
    ffprobe_binary: str = Field(default="ffprobe", title="ffprobe command", description="Prober.")
    crf: int = Field(default=20, ge=0, le=51, title="Quality (CRF)", description="Lower is better.")
    preset: str = Field(
        default="medium", title="x264 preset", description="Encoder speed versus compression."
    )
    audio_bitrate: str = Field(default="192k", title="Audio bitrate", description="AAC bitrate.")
    sample_rate: int = Field(
        default=48000, ge=8000, le=96000, title="Audio rate", description="Mix rate in Hz."
    )
    two_pass_loudness: bool = Field(
        default=True,
        title="Two-pass loudness",
        description="Measure the mix first, then normalise linearly for a more natural sound.",
    )
    true_peak_db: float = Field(
        default=-1.5, le=0.0, title="True peak", description="Maximum true peak in dBTP."
    )
    loudness_range: float = Field(
        default=11.0, ge=1.0, le=50.0, title="Loudness range", description="Target LRA in LU."
    )
    duck_threshold: float = Field(
        default=0.03,
        gt=0.0,
        le=1.0,
        title="Ducking threshold",
        description="Narration level above which the music is turned down.",
    )
    duck_max_ratio: float = Field(
        default=12.0,
        ge=1.0,
        le=20.0,
        title="Ducking ratio at full",
        description="Compression ratio applied to the music when ducking is 1.",
    )
    duck_attack_ms: float = Field(
        default=40.0, ge=0.01, le=2000, title="Ducking attack", description="Milliseconds."
    )
    duck_release_ms: float = Field(
        default=500.0, ge=0.01, le=9000, title="Ducking release", description="Milliseconds."
    )
    outline_width: float = Field(
        default=3.0, ge=0.0, title="Subtitle outline", description="Outline width in pixels."
    )
    fonts_dir: str = Field(
        default="", title="Fonts folder", description="Extra fonts for subtitles; empty is system."
    )
    timeout_seconds: float = Field(
        default=1800.0, gt=0, title="Timeout", description="Seconds allowed for one render."
    )
    probe_timeout_seconds: float = Field(
        default=60.0, gt=0, title="Probe timeout", description="Seconds allowed for probing."
    )
