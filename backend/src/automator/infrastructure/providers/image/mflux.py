from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field

from automator.domain.capabilities import Capability, ImageRequest
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.host import first_reason
from automator.infrastructure.providers.image.image_fit import fit_image, rounded_up
from automator.infrastructure.providers.seeds import prompt_seed
from automator.infrastructure.providers.spec import ProviderOptions, ProviderSpec

HF_SECRET = "huggingface_token"


class MfluxOptions(ProviderOptions):
    binary: str = Field(
        default="mflux-generate", title="Command", description="The mflux generate command."
    )
    model: Literal["schnell", "dev", "krea-dev"] = Field(
        default="schnell",
        title="Model",
        description="FLUX variant. schnell is fast; dev needs a Hugging Face token.",
    )
    steps: int = Field(
        default=4, ge=1, le=60, title="Steps", description="Denoising steps; schnell needs 2 to 4."
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


def mflux_command(request: ImageRequest, options: MfluxOptions, output: Path) -> list[str]:
    command = [
        options.binary,
        "--model",
        options.model,
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
        host = self.context.host
        return first_reason(host.not_apple_silicon(), host.missing_binary(self.options.binary))

    def generate(self, request: ImageRequest, output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        token = self.context.secret(HF_SECRET)
        self.context.runner.run(
            mflux_command(request, self.options, output),
            self.options.timeout_seconds,
            env={"HF_TOKEN": token} if token else None,
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
