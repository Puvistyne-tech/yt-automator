from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Column, ForeignKey, String, UniqueConstraint
from sqlmodel import Field, SQLModel


def payload_column() -> Any:
    return Field(sa_column=Column(JSON, nullable=False))


class CredentialRow(SQLModel, table=True):
    __tablename__ = "credentials"

    id: str = Field(primary_key=True)
    created_at: str = Field(index=True)
    payload: dict[str, Any] = payload_column()


class ChannelRow(SQLModel, table=True):
    __tablename__ = "channels"

    id: str = Field(primary_key=True)
    credential_id: str = Field(
        sa_column=Column(String, ForeignKey("credentials.id"), nullable=False, index=True)
    )
    youtube_channel_id: str = Field(unique=True)
    connected_at: str
    payload: dict[str, Any] = payload_column()


class AutomationRow(SQLModel, table=True):
    __tablename__ = "automations"

    id: str = Field(primary_key=True)
    pipeline_type: str = Field(index=True)
    enabled: bool
    created_at: str = Field(index=True)
    payload: dict[str, Any] = payload_column()


class RunRow(SQLModel, table=True):
    __tablename__ = "runs"

    id: str = Field(primary_key=True)
    automation_id: str = Field(index=True)
    status: str = Field(index=True)
    trigger: str = Field(index=True)
    created_at: str = Field(index=True)
    payload: dict[str, Any] = payload_column()


class ProviderConfigRow(SQLModel, table=True):
    __tablename__ = "provider_configs"

    capability: str = Field(primary_key=True)
    position: int
    payload: dict[str, Any] = payload_column()


class AppSettingsRow(SQLModel, table=True):
    __tablename__ = "app_settings"

    id: str = Field(primary_key=True)
    payload: dict[str, Any] = payload_column()


class QuotaEntryRow(SQLModel, table=True):
    __tablename__ = "quota_entries"
    __table_args__ = (UniqueConstraint("credential_id", "day"),)

    id: int | None = Field(default=None, primary_key=True)
    credential_id: str = Field(index=True)
    day: str = Field(index=True)
    units: int


METADATA = SQLModel.metadata
