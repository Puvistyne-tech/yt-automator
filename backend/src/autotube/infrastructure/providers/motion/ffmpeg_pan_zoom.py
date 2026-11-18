from __future__ import annotations

from pathlib import Path

from pydantic import Field

from autotube.domain.capabilities import Capability, MotionRequest
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.ffmpeg_args import X264Options
from autotube.infrastructure.providers.motion.pan_zoom_filter import (
    PanZoomTuning,
    pan_zoom_command,
)
from autotube.infrastructure.providers.output_path import ensure_parent
from autotube.infrastructure.providers.spec import ProviderSpec


class PanZoomOptions(X264Options):
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
    crf: int = Field(default=18, ge=0, le=51, title="Quality (CRF)", description="Lower is better.")
    timeout_seconds: float = Field(
        default=600.0, gt=0, title="Timeout", description="Seconds allowed for one clip."
    )


class FfmpegPanZoom:
    provider_id = "ffmpeg_pan_zoom"

    def __init__(self, options: PanZoomOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        return self.context.host.missing_binary(self.options.ffmpeg_binary)

    def tuning(self) -> PanZoomTuning:
        return PanZoomTuning(
            max_zoom=self.options.max_zoom,
            supersample=self.options.supersample,
            crf=self.options.crf,
            preset=self.options.preset,
        )

    def animate(self, request: MotionRequest, output: Path) -> Path:
        ensure_parent(output)
        command = pan_zoom_command(request, self.tuning(), self.options.ffmpeg_binary, output)
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
