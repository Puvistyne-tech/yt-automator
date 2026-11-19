from __future__ import annotations

from autotube.domain.capabilities import VideoComposition


class LogoMissingError(FileNotFoundError):
    pass


def require_logo(plan: VideoComposition) -> None:
    watermark = plan.watermark
    if watermark is not None and not watermark.image.is_file():
        raise LogoMissingError(
            f"visuals.logo_file: no picture at {str(watermark.image)!r}; choose an existing "
            "logo file or clear the field"
        )
