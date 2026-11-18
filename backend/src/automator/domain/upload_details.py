from __future__ import annotations

from collections.abc import Sequence

from automator.domain.artifact_selection import VideoMetadata
from automator.domain.channels import ChannelDefaults
from automator.domain.model_base import DomainModel

DESCRIPTION_MAX_BYTES = 5000
HASHTAG_GAP = "\n\n"


class UploadDetails(DomainModel):
    category_id: str
    default_language: str
    description: str


def utf8_size(text: str) -> int:
    return len(text.encode("utf-8"))


def with_hashtags(
    description: str, hashtags: Sequence[str], limit: int = DESCRIPTION_MAX_BYTES
) -> str:
    present = description.casefold()
    result = description
    added: list[str] = []
    for tag in hashtags:
        if tag.casefold() in present or tag in added:
            continue
        line = " ".join([*added, tag])
        candidate = f"{description}{HASHTAG_GAP}{line}" if description else line
        if utf8_size(candidate) <= limit:
            added.append(tag)
            result = candidate
    return result


def upload_details(
    metadata: VideoMetadata, defaults: ChannelDefaults, language: str
) -> UploadDetails:
    return UploadDetails(
        category_id=metadata.category_id or defaults.category_id,
        default_language=metadata.default_language or language,
        description=with_hashtags(metadata.description, metadata.hashtags),
    )
