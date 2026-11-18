from __future__ import annotations

from pathlib import Path

from pydantic import Field

from automator.domain.capabilities import Capability, MotionRequest
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.motion.pan_zoom_filter import (
    PanZoomTuning,
    pan_zoom_command,
)
from automator.infrastructure.providers.spec import ProviderOptions, ProviderSpec


class PanZoomOptions(ProviderOptions):
    binary: str = Field(default="ffmpeg", title="ffmpeg command", description="ffmpeg executable.")
    max_zoom: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        title="Zoom at full intensity",
        description="Extra zoom reached by a move at intensity 1 (0.3 means 130%).",
    )
    supersample: int = Field(
        default=3,
        ge=1,
        le=8,
        title="Supersampling",
        description="Scale the still up by this factor before moving to avoid jitter.",
    )
    crf: int = Field(
        default=18, ge=0, le=51, title="Quality (CRF)", description="Lower is better quality."
    )
    preset: str = Field(
        default="medium", title="x264 preset", description="Encoder speed versus compression."
    )
    timeout_seconds: float = Field(
        default=600.0, gt=0, title="Timeout", description="Seconds allowed for one clip."
    )


class FfmpegPanZoom:
    provider_id = "ffmpeg_pan_zoom"

    def __init__(self, options: PanZoomOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        return self.context.host.missing_binary(self.options.binary)

    def tuning(self) -> PanZoomTuning:
        return PanZoomTuning(
            max_zoom=self.options.max_zoom,
            supersample=self.options.supersample,
            crf=self.options.crf,
            preset=self.options.preset,
        )

    def animate(self, request: MotionRequest, output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        command = pan_zoom_command(request, self.tuning(), self.options.binary, output)
        self.context.runner.run(command, self.options.timeout_seconds)
        return output


SPEC = ProviderSpec(
    provider_id=FfmpegPanZoom.provider_id,
    capability=Capability.MOTION,
    name="Ken Burns (ffmpeg)",
    description="Smooth eased pan and zoom over the still image. Needs only ffmpeg.",
    options=PanZoomOptions,
    factory=FfmpegPanZoom,
    offline=True,
)
