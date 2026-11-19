from __future__ import annotations

from pathlib import Path
from typing import Final, Literal

from pydantic import Field

from autotube.domain.capabilities import Capability, ImageRequest
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.home_path import home_expanded
from autotube.infrastructure.providers.host import first_reason
from autotube.infrastructure.providers.image.image_fit import fit_image, rounded_up
from autotube.infrastructure.providers.output_path import ensure_parent
from autotube.infrastructure.providers.seeds import prompt_seed
from autotube.infrastructure.providers.spec import ProviderOptions, ProviderSpec

HF_SECRET = "huggingface_token"
MfluxModel = Literal["flux2-klein-4b", "schnell", "dev", "krea-dev"]
FLUX2_KLEIN: Final[MfluxModel] = "flux2-klein-4b"


class MfluxOptions(ProviderOptions):
    binary: str = Field(
        default="mflux-generate",
        title="Command",
        description="The mflux command for FLUX.1 models.",
    )
    model: MfluxModel = Field(
        default=FLUX2_KLEIN,
        title="Model",
        description=(
            "FLUX variant. flux2-klein-4b runs offline from Model folder; "
            "schnell, dev and krea-dev download from Hugging Face and may need a token."
        ),
    )
    flux2_binary: str = Field(
        default="mflux-generate-flux2",
        title="FLUX.2 command",
        description="The mflux command for FLUX.2 models.",
    )
    model_dir: str = Field(
        default="~/.autotube/models/black-forest-labs__FLUX.2-klein-4B",
        title="Model folder",
        description="Local FLUX.2 klein weights; a leading ~ is your home folder.",
    )
    steps: int = Field(
        default=4,
        ge=1,
        le=60,
        title="Steps",
        description="Denoising steps; klein and schnell need 2 to 4.",
    )
    quantize: Literal[3, 4, 5, 6, 8] | None = Field(
        default=8,
        title="Quantisation bits",
        description="Lower bits use less memory and run faster at some quality cost.",
    )
    reference_strength: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        title="Reference strength",
        description="How much the first reference image shapes the result (image-to-image).",
    )
    size_multiple: int = Field(
        default=16,
        ge=1,
        title="Size multiple",
        description="Width and height are rounded up to this, then the image is fitted exactly.",
    )
    timeout_seconds: float = Field(
        default=900.0, gt=0, title="Timeout", description="Seconds allowed for one image."
    )


def uses_flux2(options: MfluxOptions) -> bool:
    return options.model == FLUX2_KLEIN


def model_arguments(options: MfluxOptions) -> list[str]:
    if uses_flux2(options):
        return [options.flux2_binary, "--model", home_expanded(options.model_dir)]
    return [options.binary, "--model", options.model]


def mflux_env(options: MfluxOptions, token: str | None) -> dict[str, str] | None:
    offline = {"HF_HUB_OFFLINE": "1"} if uses_flux2(options) else {}
    env = offline | ({"HF_TOKEN": token} if token else {})
    return env or None


def mflux_command(request: ImageRequest, options: MfluxOptions, output: Path) -> list[str]:
    command = [
        *model_arguments(options),
        "--prompt",
        request.prompt,
        "--steps",
        str(options.steps),
        "--seed",
        str(prompt_seed(request.prompt, request.seed)),
        "--width",
        str(rounded_up(request.width, options.size_multiple)),
        "--height",
        str(rounded_up(request.height, options.size_multiple)),
        "--output",
        str(output),
    ]
    if options.quantize is not None:
        command += ["--quantize", str(options.quantize)]
    if request.reference_images:
        reference = str(request.reference_images[0])
        command += ["--image-path", reference, "--image-strength", str(options.reference_strength)]
    return command


class MfluxImage:
    provider_id = "mflux"

    def __init__(self, options: MfluxOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        return first_reason(self.context.host.not_apple_silicon(), *self.missing_tools())

    def missing_tools(self) -> list[str | None]:
        host = self.context.host
        if not uses_flux2(self.options):
            return [host.missing_binary(self.options.binary)]
        folder = home_expanded(self.options.model_dir)
        return [
            host.missing_binary(self.options.flux2_binary),
            host.missing_path(folder, "FLUX.2 klein model folder"),
        ]

    def generate(self, request: ImageRequest, output: Path) -> Path:
        ensure_parent(output)
        token = self.context.secret(HF_SECRET)
        self.context.runner.run(
            mflux_command(request, self.options, output),
            self.options.timeout_seconds,
            env=mflux_env(self.options, token),
        )
        return fit_image(output, request.width, request.height)


SPEC = ProviderSpec(
    provider_id=MfluxImage.provider_id,
    capability=Capability.IMAGE,
    name="FLUX (mflux)",
    description="FLUX image models running locally on Apple silicon through MLX.",
    options=MfluxOptions,
    factory=MfluxImage,
    offline=True,
)
