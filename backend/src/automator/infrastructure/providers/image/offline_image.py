from __future__ import annotations

from pathlib import Path

from pydantic import Field

from automator.domain.capabilities import Capability, ImageRequest
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.image.storybook_scene import paint_scene
from automator.infrastructure.providers.spec import ProviderOptions, ProviderSpec
from automator.shared.errors import UpstreamFailure
from automator.shared.hashing import sha256_hex


class OfflineImageOptions(ProviderOptions):
    supersample: int = Field(
        default=2,
        ge=1,
        le=4,
        title="Supersampling",
        description="Draw at this multiple of the size, then downscale for smooth edges.",
    )


def scene_seed(request: ImageRequest) -> int:
    return int(sha256_hex(f"{request.prompt}|{request.seed}")[:12], 16)


class OfflineImage:
    provider_id = "offline_image"

    def __init__(self, options: OfflineImageOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        return None

    def generate(self, request: ImageRequest, output: Path) -> Path:
        image = paint_scene(
            request.prompt,
            scene_seed(request),
            request.width,
            request.height,
            self.options.supersample,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            image.save(output)
        except (OSError, ValueError) as error:
            raise UpstreamFailure(f"cannot write image {output.name}: {error}") from error
        return output


SPEC = ProviderSpec(
    provider_id=OfflineImage.provider_id,
    capability=Capability.IMAGE,
    name="Offline storybook scene",
    description="Procedural storybook landscape drawn with Pillow. Always available.",
    options=OfflineImageOptions,
    factory=OfflineImage,
    offline=True,
)
