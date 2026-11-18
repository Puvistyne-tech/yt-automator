from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta

from automator.domain.automations import Automation, TargetFields
from automator.domain.channels import Privacy
from automator.domain.publish_outcome import is_unfinished
from automator.domain.publish_time import time_of_day_publish
from automator.domain.run_enums import UploadStatus
from automator.domain.run_parts import Upload

MAY_GO_PUBLIC: frozenset[Privacy | None] = frozenset({Privacy.PUBLIC, None})

PublishTargets = Mapping[str, TargetFields]


def publish_targets(automations: Iterable[Automation]) -> dict[str, TargetFields]:
    return {
        target.id: TargetFields.model_validate(target.model_dump(exclude={"id"}))
        for automation in automations
        for target in automation.targets
    }


def is_scheduled(upload: Upload, now: datetime) -> bool:
    return upload.publish_at is not None and upload.publish_at > now


def lacks_publish_time(upload: Upload) -> bool:
    done = upload.status is UploadStatus.DONE
    return done and upload.publish_at is None and upload.privacy in MAY_GO_PUBLIC


def latest_release(target: TargetFields, finished: datetime) -> datetime | None:
    if target.publish_time_of_day is not None:
        return time_of_day_publish(target, finished)
    return finished + timedelta(minutes=target.publish_delay_minutes)


def may_still_go_public(
    upload: Upload, finished: datetime, now: datetime, targets: PublishTargets
) -> bool:
    if not lacks_publish_time(upload):
        return False
    target = targets.get(upload.target_id)
    release = None if target is None else latest_release(target, finished)
    return release is None or release > now


def holds_run(upload: Upload, finished: datetime, now: datetime, targets: PublishTargets) -> bool:
    if is_unfinished(upload) or is_scheduled(upload, now):
        return True
    return may_still_go_public(upload, finished, now, targets)
