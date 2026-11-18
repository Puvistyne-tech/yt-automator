from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.automation_rules import automation_errors, normalized_settings
from autotube.domain.automations import Automation
from autotube.domain.quality import ReviewMode, ReviewPolicy
from autotube.domain.schedules import Schedule, ScheduleKind
from tests.fixtures.builders import automation_input, target_input
from tests.fixtures.fake_pipeline import FakePipeline, FakeSettings, kids_pipeline

PIPELINE = FakePipeline()
CHANNELS = {"chan-1", "chan-2"}
DAYTIME_HOURS: dict[str, Any] = {"active_from": "08:00", "active_until": "20:00"}
AUTO_WITH_HIGH_REJECT = ReviewPolicy(
    mode=ReviewMode.AUTO_WHEN_SCORE_AT_LEAST, min_score=70, reject_below=90
)


def errors_for(**overrides: Any) -> dict[str, str]:
    data = automation_input(**overrides)
    return automation_errors(data, PIPELINE.descriptor, PIPELINE.settings_model, CHANNELS)


def test_valid_input_has_no_errors() -> None:
    assert errors_for() == {}


def test_unknown_pipeline_is_reported() -> None:
    data = automation_input(pipeline_type="nope")
    assert automation_errors(data, None, None, CHANNELS) == {
        "pipeline_type": "unknown pipeline type 'nope'"
    }


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"settings": {"topic": ""}}, "settings.topic"),
        ({"settings": {"score": 300}}, "settings.score"),
        ({"settings": {"unknown": 1}}, "settings.unknown"),
        ({"languages": ("en", "fr")}, "languages.1"),
        ({"languages": ("en", "en")}, "languages.1"),
        ({"targets": (target_input(language="ta"),)}, "targets.0.language"),
        ({"targets": (target_input(channel_id="ghost"),)}, "targets.0.channel_id"),
        ({"targets": (target_input(variants=("landscape", "square")),)}, "targets.0.variants.1"),
        ({"schedule": Schedule(kind=ScheduleKind.INTERVAL, every_hours=0)}, "schedule.every_hours"),
        ({"schedule": Schedule(kind=ScheduleKind.CRON, cron="* *")}, "schedule.cron"),
        ({"schedule": Schedule(timezone="Bad/Zone")}, "schedule.timezone"),
        ({"schedule": Schedule(active_from="08:00")}, "schedule.active_until"),
        (
            {"schedule": Schedule(kind=ScheduleKind.CRON, cron="0 3 * * *", **DAYTIME_HOURS)},
            "schedule.active_from",
        ),
        ({"review_policy": AUTO_WITH_HIGH_REJECT}, "review_policy.reject_below"),
        (
            {"targets": (target_input(publish_time_of_day="18:00", publish_delay_minutes=5),)},
            "targets.0.publish_time_of_day",
        ),
        ({"targets": (target_input(publish_timezone="Bad/Zone"),)}, "targets.0.publish_timezone"),
    ],
)
def test_each_rule_reports_its_field_path(overrides: dict[str, Any], field: str) -> None:
    assert list(errors_for(**overrides)) == [field]


def test_errors_accumulate_across_rules() -> None:
    errors = errors_for(
        languages=("en", "xx"),
        targets=(target_input(channel_id="ghost", language="ta"),),
        schedule=Schedule(kind=ScheduleKind.INTERVAL),
    )
    assert set(errors) == {
        "languages.1",
        "targets.0.language",
        "targets.0.channel_id",
        "schedule.every_hours",
    }


def test_unknown_pipeline_still_reports_schedule_errors() -> None:
    data = automation_input(pipeline_type="nope", schedule=Schedule(kind=ScheduleKind.CRON))
    assert set(automation_errors(data, None, None, CHANNELS)) == {"pipeline_type", "schedule.cron"}


@pytest.mark.parametrize(("value", "has_error"), [(None, False), (True, False), (False, True)])
def test_kids_pipeline_refuses_targets_not_made_for_kids(
    value: bool | None, has_error: bool
) -> None:
    kids = kids_pipeline()
    data = automation_input(
        pipeline_type=kids.type_id, targets=(target_input(made_for_kids=value),)
    )
    errors = automation_errors(data, kids.descriptor, kids.settings_model, CHANNELS)
    assert ("targets.0.made_for_kids" in errors) is has_error


def test_regular_pipeline_allows_explicit_made_for_kids_choice() -> None:
    assert errors_for(targets=(target_input(made_for_kids=False),)) == {}
    assert errors_for(targets=(target_input(made_for_kids=True),)) == {}


def test_normalized_settings_fill_defaults() -> None:
    assert normalized_settings(FakeSettings, {"topic": "owls"}) == {
        "topic": "owls",
        "fail_stage": "",
        "score": 90.0,
        "with_thumbnail": True,
        "extra_meta": {},
    }


def test_automation_round_trips_to_input(automation: Automation) -> None:
    again = automation.as_input()
    assert again.name == automation.name
    assert again.targets[0].id == automation.targets[0].id
    assert automation.targets_channel("chan-1") and not automation.targets_channel("chan-9")


STORED_BEFORE_PUBLISHING_RULES: dict[str, Any] = {
    "id": "auto-1",
    "name": "Bedtime",
    "description": "",
    "pipeline_type": "fake",
    "settings": {"topic": "owls"},
    "languages": ["en"],
    "targets": [
        {
            "id": "t1",
            "channel_id": "chan-1",
            "language": "en",
            "variants": ["landscape"],
            "privacy": "public",
            "made_for_kids": None,
            "playlist_id": None,
            "publish_delay_minutes": 30,
        }
    ],
    "schedule": {"kind": "interval", "every_hours": 6, "cron": None, "timezone": "UTC"},
    "review_policy": {"mode": "auto_when_score_at_least", "min_score": 80},
    "enabled": True,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def test_an_automation_stored_before_the_publishing_rules_loads_unchanged() -> None:
    loaded = Automation.model_validate(STORED_BEFORE_PUBLISHING_RULES)
    dumped = loaded.model_dump(mode="json")
    for key, value in STORED_BEFORE_PUBLISHING_RULES.items():
        if key not in {"targets", "schedule", "review_policy"}:
            assert dumped[key] == value
    assert (
        dumped["targets"][0] | STORED_BEFORE_PUBLISHING_RULES["targets"][0] == dumped["targets"][0]
    )
    assert dumped["schedule"]["every_hours"] == 6 and dumped["schedule"]["skip_if_unfinished"]
    assert dumped["review_policy"] == {
        "mode": "auto_when_score_at_least",
        "min_score": 80.0,
        "reject_below": None,
        "auto_publish": False,
    }
    assert dumped["retry_policy"] == {"auto_retry_count": 0, "retry_delay_minutes": 10}
    assert errors_for(**loaded.as_input().model_dump(exclude={"targets"})) == {}
