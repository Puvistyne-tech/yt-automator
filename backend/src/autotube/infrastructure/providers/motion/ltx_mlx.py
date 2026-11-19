from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from autotube.domain.capabilities import Capability, MotionRequest
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.host import first_reason
from autotube.infrastructure.providers.motion.ltx_options import LtxOptions
from autotube.infrastructure.providers.motion.ltx_plan import (
    Segment,
    finish_command,
    home_expanded,
    last_frame_command,
    ltx_command,
    ltx_env,
    segment_plan,
)
from autotube.infrastructure.providers.output_path import ensure_parent, require_written
from autotube.infrastructure.providers.spec import ProviderSpec


class LtxMotion:
    provider_id = "ltx_mlx"

    def __init__(self, options: LtxOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        return first_reason(
            self.context.host.missing_binary(self.options.binary),
            self.context.host.missing_binary(self.options.ffmpeg_binary),
            self.missing_model(),
        )

    def missing_model(self) -> str | None:
        folder = home_expanded(self.options.model_dir)
        return None if Path(folder).is_dir() else f"model folder {folder} does not exist"

    def animate(self, request: MotionRequest, output: Path) -> Path:
        ensure_parent(output)
        with TemporaryDirectory(dir=output.parent, prefix=f".{output.stem}-ltx-") as work:
            plan = segment_plan(request, self.options, Path(work))
            for previous, segment in zip([None, *plan], plan, strict=False):
                self.generate(request, segment, previous)
            clips = [segment.output for segment in plan]
            self.run(finish_command(request, self.options, clips, output))
        return require_written(output, "ltx-2-mlx")

    def generate(self, request: MotionRequest, segment: Segment, previous: Segment | None) -> None:
        if previous is not None:
            binary = self.options.ffmpeg_binary
            self.run(last_frame_command(binary, previous.output, segment.image))
        self.run(ltx_command(request, self.options, segment), ltx_env(self.options))

    def run(self, command: list[str], env: dict[str, str] | None = None) -> None:
        self.context.runner.run(command, self.options.timeout_seconds, env=env)


SPEC = ProviderSpec(
    provider_id=LtxMotion.provider_id,
    capability=Capability.MOTION,
    name="LTX video (MLX)",
    description=(
        "Image-to-video with the LTX model through the ltx-2-mlx command on an Apple-silicon Mac. "
        "Longer clips are chained from short segments."
    ),
    options=LtxOptions,
    factory=LtxMotion,
    offline=True,
)
