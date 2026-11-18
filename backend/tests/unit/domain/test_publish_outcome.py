from __future__ import annotations

import pytest

from automator.domain.publish_outcome import NO_UPLOAD_SUCCEEDED, publish_outcome
from automator.domain.run_enums import RunStatus, UploadStatus
from automator.domain.run_parts import Upload

U = UploadStatus


def uploads(*statuses: UploadStatus) -> list[Upload]:
    return [
        Upload(target_id="t", channel_id="c", language="en", variant="v", status=status)
        for status in statuses
    ]


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ((U.DONE,), (RunStatus.PUBLISHED, None)),
        ((U.DONE, U.FAILED, U.SKIPPED), (RunStatus.PUBLISHED, None)),
        ((U.FAILED, U.SKIPPED), (RunStatus.APPROVED, NO_UPLOAD_SUCCEEDED)),
        ((U.DONE, U.PENDING), (RunStatus.APPROVED, NO_UPLOAD_SUCCEEDED)),
        ((U.DONE, U.UPLOADING), (RunStatus.APPROVED, NO_UPLOAD_SUCCEEDED)),
        ((), (RunStatus.APPROVED, NO_UPLOAD_SUCCEEDED)),
    ],
)
def test_publish_outcome_needs_one_done_and_nothing_unfinished(
    statuses: tuple[UploadStatus, ...], expected: tuple[RunStatus, str | None]
) -> None:
    assert publish_outcome(uploads(*statuses)) == expected
