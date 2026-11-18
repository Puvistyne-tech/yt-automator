from __future__ import annotations

from collections.abc import Iterable

from autotube.domain.automations import Automation
from autotube.domain.channels import Channel
from autotube.domain.run_state import ACTIVE_STATUSES
from autotube.domain.runs import Run
from autotube.shared.errors import RuleConflict


def ensure_channel_deletable(channel_id: str, automations: Iterable[Automation]) -> None:
    blocking = sorted(a.name for a in automations if a.enabled and a.targets_channel(channel_id))
    if blocking:
        raise RuleConflict(
            "channel_in_use",
            f"channel is targeted by enabled automations: {', '.join(blocking)}",
        )


def ensure_credential_deletable(credential_id: str, channels: Iterable[Channel]) -> None:
    using = sorted(channel.title for channel in channels if channel.credential_id == credential_id)
    if using:
        raise RuleConflict(
            "credential_in_use", f"credential is used by channels: {', '.join(using)}"
        )


def ensure_run_deletable(run: Run) -> None:
    if run.status in ACTIVE_STATUSES:
        raise RuleConflict(
            "run_active", f"run {run.id} is {run.status.value}; cancel it before deleting"
        )
