from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from automator.domain.capabilities import Capability
from automator.domain.providers import ProviderChoice, ProviderConfig
from automator.domain.run_enums import RunStatus, RunTrigger
from automator.domain.runs import RunQuery
from automator.domain.settings import AppSettings
from automator.infrastructure.db.database import Database
from automator.infrastructure.db.entity_repositories import (
    SqlAutomationRepository,
    SqlChannelRepository,
    SqlCredentialRepository,
)
from automator.infrastructure.db.run_repository import SqlRunRepository
from automator.infrastructure.db.settings_repositories import (
    SqlAppSettingsRepository,
    SqlProviderConfigRepository,
    SqlQuotaLedger,
)
from tests.fixtures.fake_runtime import START
from tests.unit.infrastructure.records import automation, channel, credential, run


def test_migrations_are_idempotent_and_enable_wal(database: Database) -> None:
    database.migrate()
    with database.engine.connect() as connection:
        assert connection.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1


@pytest.mark.parametrize(
    ("repository_type", "model"),
    [
        (SqlCredentialRepository, credential()),
        (SqlChannelRepository, channel()),
        (SqlAutomationRepository, automation()),
        (SqlRunRepository, run("run-1")),
    ],
)
def test_entities_round_trip_losslessly(
    database: Database, repository_type: Any, model: BaseModel
) -> None:
    SqlCredentialRepository(database).save(credential())
    repository = repository_type(database)
    repository.save(model)
    model_id = model.model_dump()["id"]
    assert repository.get(model_id) == model
    repository.delete(model_id)
    assert repository.get(model_id) is None
    repository.delete(model_id)


def test_save_overwrites_and_list_orders_by_creation(database: Database) -> None:
    repository = SqlCredentialRepository(database)
    later = credential("cred-2").model_copy(update={"created_at": START + timedelta(days=1)})
    repository.save(later)
    repository.save(credential())
    repository.save(credential().model_copy(update={"name": "Renamed"}))
    assert [item.name for item in repository.list()] == ["Renamed", "Project"]


def test_channels_are_unique_per_youtube_id_and_need_a_credential(database: Database) -> None:
    channels = SqlChannelRepository(database)
    with pytest.raises(IntegrityError):
        channels.save(channel())
    SqlCredentialRepository(database).save(credential())
    channels.save(channel())
    assert channels.find_by_youtube_id("UC-1") == channel()
    assert channels.find_by_youtube_id("UC-missing") is None
    with pytest.raises(IntegrityError):
        channels.save(channel("chan-2"))


@pytest.fixture
def stored_runs(database: Database) -> SqlRunRepository:
    runs = SqlRunRepository(database)
    runs.save(run("r1", 0))
    runs.save(run("r2", 10, status=RunStatus.AWAITING_REVIEW))
    runs.save(run("r3", 20, automation_id="auto-2", trigger=RunTrigger.SCHEDULE))
    runs.save(run("r4", 30, status=RunStatus.AWAITING_REVIEW))
    return runs


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (RunQuery(), ["r4", "r3", "r2", "r1"]),
        (RunQuery(limit=2), ["r4", "r3"]),
        (RunQuery(automation_id="auto-2"), ["r3"]),
        (RunQuery(status=RunStatus.AWAITING_REVIEW), ["r4", "r2"]),
        (RunQuery(trigger=RunTrigger.SCHEDULE), ["r3"]),
        (RunQuery(created_after=START + timedelta(minutes=10)), ["r4", "r3", "r2"]),
        (RunQuery(automation_id="auto-1", status=RunStatus.AWAITING_REVIEW, limit=1), ["r4"]),
    ],
)
def test_run_queries_filter_in_sql_newest_first(
    stored_runs: SqlRunRepository, query: RunQuery, expected: list[str]
) -> None:
    assert [item.id for item in stored_runs.list(query)] == expected


def test_status_change_is_visible_to_queries(stored_runs: SqlRunRepository) -> None:
    stored_runs.save(run("r1", 0, status=RunStatus.AWAITING_REVIEW))
    found = stored_runs.list(RunQuery(status=RunStatus.AWAITING_REVIEW))
    assert [item.id for item in found] == ["r4", "r2", "r1"]


def test_provider_configs_keep_their_order(database: Database) -> None:
    repository = SqlProviderConfigRepository(database)
    configs = [
        ProviderConfig(capability=Capability.TTS, chain=(ProviderChoice(provider_id="a"),)),
        ProviderConfig(
            capability=Capability.LLM,
            chain=(ProviderChoice(provider_id="b", enabled=False, options={"t": 0.2}),),
        ),
    ]
    repository.save_all(configs)
    assert repository.list() == configs
    repository.save_all(configs[1:])
    assert repository.list() == configs[1:]


def test_app_settings_default_and_report_the_data_dir(database: Database) -> None:
    repository = SqlAppSettingsRepository(database, "/data")
    assert repository.get() == AppSettings(data_dir="/data")
    repository.save(AppSettings(timezone="Asia/Kolkata", max_parallel_runs=3, data_dir="/x"))
    assert repository.get() == AppSettings(
        timezone="Asia/Kolkata", max_parallel_runs=3, data_dir="/data"
    )


def test_quota_ledger_accumulates_per_credential_and_day(database: Database) -> None:
    ledger = SqlQuotaLedger(database)
    today, tomorrow = date(2026, 1, 5), date(2026, 1, 6)
    ledger.record("cred-1", 1600, today)
    ledger.record("cred-1", 50, today)
    ledger.record("cred-1", 400, tomorrow)
    ledger.record("cred-2", 7, today)
    assert ledger.used_today("cred-1", today) == 1650
    assert ledger.used_today("cred-1", tomorrow) == 400
    assert ledger.used_today("cred-2", today) == 7
    assert ledger.used_today("cred-3", today) == 0
