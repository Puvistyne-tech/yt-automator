from __future__ import annotations

from pathlib import Path

from pydantic import Field

from automator.domain.capabilities import CameraMove, Capability, MotionRequest
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.spec import ProviderOptions, ProviderSpec

DEFAULT_PRESETS: dict[CameraMove, str] = {
    CameraMove.PUSH_IN: "dolly",
    CameraMove.PULL_OUT: "dolly --reverse",
    CameraMove.PAN_LEFT: "horizontal --reverse",
    CameraMove.PAN_RIGHT: "horizontal",
    CameraMove.RISE: "vertical",
    CameraMove.STILL: "",
}


class DepthflowOptions(ProviderOptions):
    binary: str = Field(default="depthflow", title="Command", description="DepthFlow executable.")
    intensity_min: float = Field(
        default=0.2,
        ge=0.0,
        title="Intensity at 0",
        description="DepthFlow parallax intensity used for a request intensity of 0.",
    )
    intensity_max: float = Field(
        default=1.2,
        ge=0.0,
        title="Intensity at 1",
        description="DepthFlow parallax intensity used for a request intensity of 1.",
    )
    camera_presets: dict[CameraMove, str] = Field(
        default_factory=lambda: dict(DEFAULT_PRESETS),
        title="Camera presets",
        description="DepthFlow animation command and flags for each camera move; empty is static.",
    )
    ssaa: float = Field(
        default=1.5, ge=1.0, le=4.0, title="Supersampling", description="Render anti-aliasing."
    )
    quality: int = Field(
        default=50, ge=0, le=100, title="Quality", description="Ray-marching quality."
    )
    timeout_seconds: float = Field(
        default=900.0, gt=0, title="Timeout", description="Seconds allowed for one clip."
    )


def mapped_intensity(request: MotionRequest, options: DepthflowOptions) -> float:
    span = options.intensity_max - options.intensity_min
    return round(options.intensity_min + span * request.intensity, 4)


def animation_args(request: MotionRequest, options: DepthflowOptions) -> list[str]:
    preset = options.camera_presets.get(request.camera, "").split()
    if not preset:
        return []
    return [*preset, "--intensity", str(mapped_intensity(request, options))]


def depthflow_command(request: MotionRequest, options: DepthflowOptions, output: Path) -> list[str]:
    return [
        options.binary,
        "input",
        "-i",
        str(request.image),
        *animation_args(request, options),
        "main",
        "-o",
        str(output),
        "-w",
        str(request.width),
        "-h",
        str(request.height),
        "-f",
        str(request.fps),
        "-t",
        f"{request.duration_seconds:g}",
        "--ssaa",
        f"{options.ssaa:g}",
        "--quality",
        str(options.quality),
    ]


class DepthflowMotion:
    provider_id = "depthflow"

    def __init__(self, options: DepthflowOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        return self.context.host.missing_binary(self.options.binary)

    def animate(self, request: MotionRequest, output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        command = depthflow_command(request, self.options, output)
        self.context.runner.run(command, self.options.timeout_seconds)
        return output


SPEC = ProviderSpec(
    provider_id=DepthflowMotion.provider_id,
    capability=Capability.MOTION,
    name="DepthFlow parallax",
    description="2.5D parallax from an estimated depth map. Runs as a separate AGPL process.",
    options=DepthflowOptions,
    factory=DepthflowMotion,
    offline=True,
)
