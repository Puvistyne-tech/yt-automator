from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field

from automator.domain.capabilities import Capability, MusicRequest
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.host import first_reason
from automator.infrastructure.providers.music.audio_fit import AudioFitOptions, fit_audio_command
from automator.infrastructure.providers.output_path import ensure_parent
from automator.infrastructure.providers.seeds import prompt_seed
from automator.infrastructure.providers.spec import ProviderSpec

ACE_STEP_SCRIPT = (
    "import json, sys\n"
    "from acestep.pipeline_ace_step import ACEStepPipeline\n"
    "job = json.load(sys.stdin)\n"
    "pipeline = ACEStepPipeline(checkpoint_dir=job.pop('checkpoint_dir') or None)\n"
    "pipeline(**job)\n"
)


class AceStepOptions(AudioFitOptions):
    python_executable: str = Field(
        default="",
        title="ACE-Step Python",
        description="Python of a separate venv with ace-step installed. "
        "Empty means <data dir>/tools/ace-step/bin/python.",
    )
    checkpoint_dir: str = Field(
        default="", title="Checkpoint folder", description="Model folder; empty downloads it."
    )
    steps: int = Field(default=27, ge=1, le=200, title="Steps", description="Inference steps.")
    guidance_scale: float = Field(
        default=15.0,
        gt=0,
        title="Guidance",
        description="How closely the music follows the prompt.",
    )
    lyrics: str = Field(
        default="[instrumental]", title="Lyrics", description="Lyrics, or [instrumental]."
    )
    render_timeout_seconds: float = Field(
        default=1800.0, gt=0, title="Render timeout", description="Seconds allowed for the model."
    )


def ace_step_job(request: MusicRequest, options: AceStepOptions, raw: Path) -> str:
    job = {
        "checkpoint_dir": options.checkpoint_dir,
        "audio_duration": request.duration_seconds,
        "prompt": request.prompt,
        "lyrics": options.lyrics,
        "infer_step": options.steps,
        "guidance_scale": options.guidance_scale,
        "manual_seeds": [prompt_seed(request.prompt)],
        "save_path": str(raw),
    }
    return json.dumps(job)


class AceStepMusic:
    provider_id = "ace_step"

    def __init__(self, options: AceStepOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def python(self) -> Path:
        if self.options.python_executable:
            return Path(self.options.python_executable)
        return self.context.data_dir / "tools" / "ace-step" / "bin" / "python"

    def available(self) -> str | None:
        python = self.python()
        missing = None if python.is_file() else f"no ACE-Step venv at {python}"
        return first_reason(missing, self.context.host.missing_binary(self.options.ffmpeg_binary))

    def compose(self, request: MusicRequest, output: Path) -> Path:
        ensure_parent(output)
        raw = output.with_suffix(".ace.wav")
        runner = self.context.runner
        try:
            runner.run(
                [str(self.python()), "-c", ACE_STEP_SCRIPT],
                self.options.render_timeout_seconds,
                stdin=ace_step_job(request, self.options, raw),
            )
            command = fit_audio_command(raw, output, request.duration_seconds, self.options)
            runner.run(command, self.options.timeout_seconds)
        finally:
            raw.unlink(missing_ok=True)
        return output


SPEC = ProviderSpec(
    provider_id=AceStepMusic.provider_id,
    capability=Capability.MUSIC,
    name="ACE-Step (local)",
    description="Text-to-music model run in its own Python environment. Slow but original.",
    options=AceStepOptions,
    factory=AceStepMusic,
    offline=True,
)
