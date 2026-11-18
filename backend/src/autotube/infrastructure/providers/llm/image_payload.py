from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from autotube.domain.capabilities import TextRequest
from autotube.shared.errors import UpstreamFailure


def image_mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "image/png"


def image_base64(path: Path) -> str:
    try:
        return base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError as error:
        raise UpstreamFailure(f"cannot read image {path.name}: {error}") from error


def reject_images(provider_id: str, request: TextRequest) -> None:
    if request.images:
        raise UpstreamFailure(f"{provider_id} does not accept image input", "vision_unsupported")
