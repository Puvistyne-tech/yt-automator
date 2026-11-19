from __future__ import annotations

from autotube.pipelines.narrated_video.publishing.metadata import UploadMetadata
from autotube.pipelines.narrated_video.story.child_terms import (
    child_term_message,
    child_terms_in_any,
)


class ChildDirectedMetadataError(RuntimeError):
    pass


def metadata_texts(metadata: UploadMetadata) -> list[str]:
    return [
        metadata.title,
        metadata.description,
        metadata.playlist_title,
        *metadata.tags,
        *metadata.hashtags,
    ]


def checked_audience(metadata: UploadMetadata) -> UploadMetadata:
    if metadata.made_for_kids:
        return metadata
    found = child_terms_in_any(metadata_texts(metadata))
    if found:
        raise ChildDirectedMetadataError(
            f"{metadata.default_language} upload details for a general audience must "
            f"{child_term_message(found)}"
        )
    return metadata
