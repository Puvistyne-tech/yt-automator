from __future__ import annotations

from sqlmodel import select

from autotube.domain.automations import Automation
from autotube.domain.channels import Channel
from autotube.domain.credentials import Credential
from autotube.infrastructure.db.codec import sortable_time, to_payload
from autotube.infrastructure.db.database import Database
from autotube.infrastructure.db.row_repository import RowRepository
from autotube.infrastructure.db.tables import AutomationRow, ChannelRow, CredentialRow


def credential_row(credential: Credential) -> CredentialRow:
    return CredentialRow(
        id=credential.id,
        created_at=sortable_time(credential.created_at),
        payload=to_payload(credential),
    )


def channel_row(channel: Channel) -> ChannelRow:
    return ChannelRow(
        id=channel.id,
        credential_id=channel.credential_id,
        youtube_channel_id=channel.youtube_channel_id,
        connected_at=sortable_time(channel.connected_at),
        payload=to_payload(channel),
    )


def automation_row(automation: Automation) -> AutomationRow:
    return AutomationRow(
        id=automation.id,
        pipeline_type=automation.pipeline_type,
        enabled=automation.enabled,
        created_at=sortable_time(automation.created_at),
        payload=to_payload(automation),
    )


class SqlCredentialRepository(RowRepository[Credential, CredentialRow]):
    def __init__(self, db: Database) -> None:
        super().__init__(db, CredentialRow, Credential, credential_row, "created_at")


class SqlChannelRepository(RowRepository[Channel, ChannelRow]):
    def __init__(self, db: Database) -> None:
        super().__init__(db, ChannelRow, Channel, channel_row, "connected_at")

    def find_by_youtube_id(self, youtube_channel_id: str) -> Channel | None:
        statement = select(ChannelRow).where(ChannelRow.youtube_channel_id == youtube_channel_id)
        with self.db.session() as session:
            row = session.exec(statement).first()
            return self.decode(row) if row is not None else None


class SqlAutomationRepository(RowRepository[Automation, AutomationRow]):
    def __init__(self, db: Database) -> None:
        super().__init__(db, AutomationRow, Automation, automation_row, "created_at")
