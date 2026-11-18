from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta

from automator.domain.automations import Automation
from automator.domain.channels import Privacy
from automator.domain.publish_outcome import is_unfinished
from automator.domain.run_enums import UploadStatus
from automator.domain.run_parts import Upload

MAY_GO_PUBLIC: frozenset[Privacy | None] = frozenset({Privacy.PUBLIC, None})


def publish_delays(automations: Iterable[Automation]) -> dict[str, int]:
    return {
        target.id: target.publish_delay_minutes
        for automation in automations
        for target in automation.targets
    }


def is_scheduled(upload: Upload, now: datetime) -> bool:
    return upload.publish_at is not None and upload.publish_at > now


def lacks_publish_time(upload: Upload) -> bool:
    done = upload.status is UploadStatus.DONE
    return done and upload.publish_at is None and upload.privacy in MAY_GO_PUBLIC


def may_still_go_public(
    upload: Upload, finished: datetime, now: datetime, delays: Mapping[str, int]
) -> bool:
    if not lacks_publish_time(upload):
        return False
    delay = delays.get(upload.target_id)
    return delay is None or finished + timedelta(minutes=delay) > now


def holds_run(upload: Upload, finished: datetime, now: datetime, delays: Mapping[str, int]) -> bool:
    if is_unfinished(upload) or is_scheduled(upload, now):
        return True
    return may_still_go_public(upload, finished, now, delays)
