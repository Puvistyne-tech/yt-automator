from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import Session, col, select

from automator.domain.providers import ProviderConfig
from automator.domain.settings import AppSettings, AppSettingsInput
from automator.domain.settings_overrides import (
    Overrides,
    effective_settings,
    storable_settings,
    stored_settings,
)
from automator.infrastructure.db.codec import from_payload, to_payload
from automator.infrastructure.db.database import Database
from automator.infrastructure.db.tables import AppSettingsRow, ProviderConfigRow, QuotaEntryRow

APP_SETTINGS_ID = "app"


class SqlProviderConfigRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list(self) -> list[ProviderConfig]:
        with self.db.session() as session:
            rows = session.exec(select(ProviderConfigRow).order_by(col(ProviderConfigRow.position)))
            return [from_payload(ProviderConfig, row.payload) for row in rows.all()]

    def save_all(self, configs: Sequence[ProviderConfig]) -> None:
        with self.db.session() as session:
            session.execute(delete(ProviderConfigRow))
            for position, config in enumerate(configs):
                session.add(
                    ProviderConfigRow(
                        capability=config.capability.value,
                        position=position,
                        payload=to_payload(config),
                    )
                )


class SqlAppSettingsRepository:
    def __init__(self, db: Database, data_dir: str, overrides: Overrides = ()) -> None:
        self.db = db
        self.data_dir = data_dir
        self.overrides = tuple(overrides)

    def stored(self, session: Session) -> AppSettingsInput:
        row = session.get(AppSettingsRow, APP_SETTINGS_ID)
        return stored_settings(row.payload if row is not None else None)

    def get(self) -> AppSettings:
        with self.db.session() as session:
            stored = self.stored(session)
        return effective_settings(stored, self.overrides, self.data_dir)

    def save(self, settings: AppSettings) -> None:
        with self.db.immediate_session() as session:
            kept = storable_settings(settings.input(), self.stored(session), list(settings.locked))
            session.merge(AppSettingsRow(id=APP_SETTINGS_ID, payload=to_payload(kept)))


class SqlQuotaLedger:
    def __init__(self, db: Database) -> None:
        self.db = db

    def used_today(self, credential_id: str, day: date) -> int:
        statement = select(QuotaEntryRow.units).where(
            QuotaEntryRow.credential_id == credential_id, QuotaEntryRow.day == day.isoformat()
        )
        with self.db.session() as session:
            return session.exec(statement).first() or 0

    def record(self, credential_id: str, units: int, day: date) -> None:
        statement = insert(QuotaEntryRow).values(
            credential_id=credential_id, day=day.isoformat(), units=units
        )
        upsert = statement.on_conflict_do_update(
            index_elements=["credential_id", "day"],
            set_={"units": QuotaEntryRow.units + statement.excluded.units},
        )
        with self.db.session() as session:
            session.execute(upsert)
