from __future__ import annotations

from collections.abc import Sequence

from automator.domain.run_enums import RunStatus, UploadStatus
from automator.domain.run_parts import Upload

NO_UPLOAD_SUCCEEDED = "no upload succeeded"
UNFINISHED_UPLOADS = frozenset({UploadStatus.PENDING, UploadStatus.UPLOADING})


def is_unfinished(upload: Upload) -> bool:
    return upload.status in UNFINISHED_UPLOADS


def publish_outcome(uploads: Sequence[Upload]) -> tuple[RunStatus, str | None]:
    done = any(upload.status is UploadStatus.DONE for upload in uploads)
    if done and not any(is_unfinished(upload) for upload in uploads):
        return RunStatus.PUBLISHED, None
    return RunStatus.APPROVED, NO_UPLOAD_SUCCEEDED
