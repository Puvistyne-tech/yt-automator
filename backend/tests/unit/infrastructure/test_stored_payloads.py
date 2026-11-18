from __future__ import annotations

from typing import Any

from autotube.domain.quality import ReviewPolicy
from autotube.domain.retries import RetryPolicy
from autotube.infrastructure.db.database import Database
from autotube.infrastructure.db.entity_repositories import SqlAutomationRepository
from autotube.infrastructure.db.run_repository import SqlRunRepository
from autotube.infrastructure.db.tables import AutomationRow, RunRow

CREATED = "2026-01-01T00:00:00Z"
OLD_TARGET: dict[str, Any] = {
    "id": "t1",
    "channel_id": "chan-1",
    "language": "en",
    "variants": ["landscape"],
    "privacy": "public",
    "made_for_kids": None,
    "playlist_id": None,
    "publish_delay_minutes": 45,
}
OLD_AUTOMATION: dict[str, Any] = {
    "id": "auto-old",
    "name": "Older automation",
    "description": "",
    "pipeline_type": "fake",
    "settings": {"topic": "owls"},
    "languages": ["en"],
    "targets": [OLD_TARGET],
    "schedule": {"kind": "cron", "every_hours": None, "cron": "0 9 * * *", "timezone": "UTC"},
    "review_policy": {"mode": "always", "min_score": 85.0},
    "enabled": True,
    "created_at": CREATED,
    "updated_at": CREATED,
    "next_run_at": None,
    "last_run": None,
}
OLD_RUN: dict[str, Any] = {
    "id": "run-old",
    "automation_id": "auto-old",
    "automation_name": "Older automation",
    "pipeline_type": "fake",
    "status": "failed",
    "trigger": "schedule",
    "languages": ["en"],
    "settings_snapshot": {"topic": "owls"},
    "review_policy": {"mode": "always", "min_score": 85.0},
    "uploads": [
        {"target_id": "t1", "channel_id": "chan-1", "language": "en", "variant": "landscape"}
    ],
    "error": "boom",
    "created_at": CREATED,
}


def insert_old_rows(database: Database) -> None:
    with database.immediate_session() as session:
        session.add(
            AutomationRow(
                id="auto-old",
                pipeline_type="fake",
                enabled=True,
                created_at=CREATED,
                payload=OLD_AUTOMATION,
            )
        )
        session.add(
            RunRow(
                id="run-old",
                automation_id="auto-old",
                status="failed",
                trigger="schedule",
                created_at=CREATED,
                payload=OLD_RUN,
            )
        )


def test_an_automation_stored_before_the_publishing_rules_loads_unchanged(
    database: Database,
) -> None:
    insert_old_rows(database)
    loaded = SqlAutomationRepository(database).get("auto-old")
    assert loaded is not None
    target = loaded.targets[0]
    assert (target.privacy, target.publish_delay_minutes) == ("public", 45)
    assert (target.publish_time_of_day, target.publish_timezone) == (None, "UTC")
    assert loaded.schedule.cron == "0 9 * * *" and loaded.schedule.skip_if_unfinished
    assert loaded.schedule.max_runs_per_day is None and loaded.schedule.active_from is None
    assert loaded.review_policy == ReviewPolicy()
    assert loaded.retry_policy == RetryPolicy()
    dumped = loaded.model_dump(mode="json")
    for key in ("schedule", "review_policy"):
        assert dumped[key] | OLD_AUTOMATION[key] == dumped[key]
    assert dumped["targets"][0] | OLD_TARGET == dumped["targets"][0]
    unchanged = OLD_AUTOMATION.keys() - {"schedule", "review_policy", "targets"}
    assert {key: dumped[key] for key in unchanged} == {
        key: OLD_AUTOMATION[key] for key in unchanged
    }


def test_a_run_stored_before_retries_loads_with_nothing_pending(database: Database) -> None:
    insert_old_rows(database)
    loaded = SqlRunRepository(database).get("run-old")
    assert loaded is not None
    assert (loaded.auto_retries, loaded.retry_at, loaded.skipped_start_at) == (0, None, None)
    assert loaded.retry_policy == RetryPolicy() and loaded.uploads[0].publish_at is None
