from __future__ import annotations

from typing import Any

from automator.domain.diagnostic_rules import GIB
from automator.domain.diagnostics import SystemFacts
from automator.shared.errors import RuleConflict

HEALTHY_FACTS: dict[str, Any] = {
    "python_version": "3.12.4",
    "data_dir": "/data",
    "data_dir_writable": True,
    "free_bytes": 50 * GIB,
    "ffmpeg_version": "ffmpeg version 7.1",
    "ffprobe_version": "ffprobe version 7.1",
    "database_path": "/data/automator.db",
    "database_revision": "0001",
    "database_head": "0001",
    "web_dist_dir": "/web/dist",
    "ui_built": True,
}


def system_facts(**changes: Any) -> SystemFacts:
    return SystemFacts.model_validate(HEALTHY_FACTS | changes)


class FakeInspector:
    def __init__(self, facts: SystemFacts | None = None) -> None:
        self.current = facts or system_facts()

    def facts(self) -> SystemFacts:
        return self.current


class UnreadableSecrets:
    def get(self, name: str) -> str | None:
        raise RuleConflict("secrets_unreadable", f"cannot read {name}")

    def set(self, name: str, value: str) -> None:
        raise RuleConflict("secrets_unreadable", f"cannot write {name}={len(value)}")

    def delete(self, name: str) -> None:
        raise RuleConflict("secrets_unreadable", f"cannot delete {name}")

    def has(self, name: str) -> bool:
        raise RuleConflict("secrets_unreadable", f"cannot read {name}")
