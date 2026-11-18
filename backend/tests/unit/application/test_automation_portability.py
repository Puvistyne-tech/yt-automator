from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pytest

from autotube.application.export_automation import ExportAutomation
from autotube.application.import_automation import ImportAutomation
from autotube.domain.automations import Automation
from autotube.domain.channels import channel_token_secret_name
from autotube.domain.credentials import credential_secret_name
from autotube.domain.quality import ReviewMode, ReviewPolicy
from autotube.domain.retries import RetryPolicy
from autotube.domain.schedules import Schedule, ScheduleKind
from autotube.shared.errors import NotFound, ValidationFailed
from tests.fixtures.builders import (
    add_automation,
    add_channel,
    create_automation,
    target_input,
)
from tests.fixtures.harness import Harness

pytestmark = pytest.mark.usefixtures("channel")


def exporter(harness: Harness) -> ExportAutomation:
    return ExportAutomation(harness.automations, harness.channels, harness.pipelines, harness.clock)


def importer(harness: Harness) -> ImportAutomation:
    return ImportAutomation(harness.channels, harness.builder, create_automation(harness))


def exported(harness: Harness, automation: Automation) -> dict[str, Any]:
    dumped: dict[str, Any] = exporter(harness).execute(automation.id).model_dump(mode="json")
    return dumped


def test_export_stamps_time_and_never_carries_secrets(
    harness: Harness, automation: Automation
) -> None:
    document = exported(harness, automation)
    text = json.dumps(document)
    assert datetime.fromisoformat(document["exported_at"]) == harness.clock.now()
    assert document["automation"]["settings"] == automation.settings
    for secret_name in (credential_secret_name("cred-1"), channel_token_secret_name("chan-1")):
        value = harness.secrets.get(secret_name)
        assert value is not None and value not in text
    assert "token" not in text and "secret" not in text and "cred-1" not in text


def test_export_unknown_automation(harness: Harness) -> None:
    with pytest.raises(NotFound):
        exporter(harness).execute("missing")


def test_import_creates_disabled_copy_with_new_ids(
    harness: Harness, automation: Automation
) -> None:
    created = importer(harness).execute(exported(harness, automation), {})
    assert created.id != automation.id
    assert (created.name, created.enabled) == ("Bedtime (imported)", False)
    assert created.settings == automation.settings
    assert created.targets[0].channel_id == "chan-1"
    assert created.targets[0].id != automation.targets[0].id
    assert harness.automations.get(created.id) == created


def test_import_fills_settings_and_rules_missing_from_old_exports(
    harness: Harness, automation: Automation
) -> None:
    document = exported(harness, automation)
    document["automation"]["settings"] = {"topic": "owls"}
    del document["automation"]["retry_policy"]
    created = importer(harness).execute(document, {})
    assert created.settings["score"] == 90.0 and created.retry_policy.auto_retry_count == 0


def test_import_unknown_pipeline_is_a_field_error(harness: Harness, automation: Automation) -> None:
    document = exported(harness, automation)
    document["automation"]["pipeline_type"] = "missing"
    with pytest.raises(ValidationFailed) as raised:
        importer(harness).preview(document, {})
    assert "automation.pipeline_type" in raised.value.fields
    assert len(harness.automations.list()) == 1


def test_round_trip_keeps_every_rule_language_and_target(harness: Harness) -> None:
    source = add_automation(
        harness,
        description="Nightly",
        languages=("en", "ta"),
        targets=(
            target_input(variants=("landscape", "short"), publish_delay_minutes=30),
            target_input(language="ta", variants=("short",), playlist_id="pl-1"),
        ),
        schedule=Schedule(kind=ScheduleKind.INTERVAL, every_hours=6, max_runs_per_day=2),
        review_policy=ReviewPolicy(
            mode=ReviewMode.AUTO_WHEN_SCORE_AT_LEAST, min_score=90, reject_below=50
        ),
        retry_policy=RetryPolicy(auto_retry_count=2, retry_delay_minutes=15),
    )
    created = importer(harness).execute(exported(harness, source), {})
    kept = {"id", "name", "enabled", "created_at", "updated_at", "targets", "next_run_at"}
    assert created.model_dump(exclude=kept) == source.model_dump(exclude=kept)
    without_ids = [target.model_dump(exclude={"id"}) for target in created.targets]
    assert without_ids == [target.model_dump(exclude={"id"}) for target in source.targets]


def test_enabled_in_a_document_still_imports_disabled(
    harness: Harness, automation: Automation
) -> None:
    document = exported(harness, automation)
    document["automation"]["enabled"] = True
    assert importer(harness).execute(document, {}).enabled is False


def test_machine_local_settings_never_travel(harness: Harness) -> None:
    source = add_automation(harness, settings={"topic": "owls", "font_file": "/Users/me/a.ttf"})
    document = exported(harness, source)
    assert document["automation"]["settings"]["font_file"] == ""
    document["automation"]["settings"]["font_file"] = "/Users/someone/b.ttf"
    assert importer(harness).execute(document, {}).settings["font_file"] == ""


def test_preview_lists_unknown_channels_without_failing(
    harness: Harness, automation: Automation
) -> None:
    document = exported(harness, automation)
    harness.channels.delete("chan-1")
    preview = importer(harness).preview(document, {})
    assert [item.id for item in preview.unknown_channels] == ["chan-1"]
    assert preview.unknown_channels[0].title == "Channel chan-1"
    assert preview.automation.name == "Bedtime (imported)"


def test_import_with_unknown_channel_needs_a_choice(
    harness: Harness, automation: Automation
) -> None:
    document = exported(harness, automation)
    harness.channels.delete("chan-1")
    with pytest.raises(ValidationFailed) as raised:
        importer(harness).execute(document, {})
    assert set(raised.value.fields) == {"channel_map.chan-1"}
    assert "choose a channel" in raised.value.fields["channel_map.chan-1"]


def test_import_maps_or_leaves_out_unknown_channels(
    harness: Harness, automation: Automation
) -> None:
    document = exported(harness, automation)
    harness.channels.delete("chan-1")
    add_channel(harness, "chan-2", youtube_id="UC-other")
    mapped = importer(harness).execute(document, {"chan-1": "chan-2"})
    assert [target.channel_id for target in mapped.targets] == ["chan-2"]
    left_out = importer(harness).execute(document, {"chan-1": None})
    assert left_out.targets == ()


def test_import_matches_a_reconnected_channel_by_youtube_id(
    harness: Harness, automation: Automation
) -> None:
    document = exported(harness, automation)
    harness.channels.delete("chan-1")
    add_channel(harness, "chan-9", youtube_id="UC-chan-1")
    preview = importer(harness).preview(document, {})
    assert preview.unknown_channels == ()
    assert preview.automation.targets[0].channel_id == "chan-9"


def test_import_choice_of_missing_channel_is_a_field_error(
    harness: Harness, automation: Automation
) -> None:
    document = exported(harness, automation)
    with pytest.raises(ValidationFailed) as raised:
        importer(harness).preview(document, {"chan-1": "nope"})
    assert set(raised.value.fields) == {"channel_map.chan-1"}


def test_import_reports_rule_errors_under_automation(
    harness: Harness, automation: Automation
) -> None:
    document = exported(harness, automation)
    document["automation"]["settings"] = {"topic": ""}
    document["automation"]["targets"] = [
        target_input(language="ta").model_dump(mode="json", exclude={"id"})
    ]
    with pytest.raises(ValidationFailed) as raised:
        importer(harness).execute(document, {})
    assert set(raised.value.fields) == {
        "automation.settings.topic",
        "automation.targets.0.language",
    }
