from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from autotube.domain.artifact_selection import VideoMetadata
from autotube.domain.channels import ChannelDefaults
from autotube.domain.model_base import DomainModel

DESCRIPTION_MAX_BYTES = 5000
HASHTAGS_MAX = 60
HASHTAG = re.compile(r"#\S+")
HASHTAG_GAP = "\n\n"


class UploadDetails(DomainModel):
    category_id: str
    default_language: str
    description: str


def utf8_length(text: str) -> int:
    return len(text.encode("utf-8"))


def hashtags_in(text: str) -> set[str]:
    return {token.casefold() for token in text.split() if HASHTAG.fullmatch(token)}


def valid_hashtags(hashtags: Iterable[str]) -> list[str]:
    kept: dict[str, str] = {}
    for raw in hashtags:
        tag = raw.strip()
        if HASHTAG.fullmatch(tag):
            kept.setdefault(tag.casefold(), tag)
    return list(kept.values())


def appended(description: str, added: Sequence[str]) -> str:
    line = " ".join(added)
    if not line:
        return description
    return f"{description}{HASHTAG_GAP}{line}" if description else line


def with_hashtags(
    description: str, hashtags: Sequence[str], limit: int = DESCRIPTION_MAX_BYTES
) -> str:
    present = hashtags_in(description)
    room = HASHTAGS_MAX - len(present)
    added: list[str] = []
    for tag in valid_hashtags(hashtags):
        if tag.casefold() in present or len(added) >= room:
            continue
        if utf8_length(appended(description, [*added, tag])) <= limit:
            added.append(tag)
    return appended(description, added)


def upload_details(
    metadata: VideoMetadata, defaults: ChannelDefaults, language: str
) -> UploadDetails:
    return UploadDetails(
        category_id=metadata.category_id or defaults.category_id,
        default_language=metadata.default_language or language,
        description=with_hashtags(metadata.description, metadata.hashtags),
    )
