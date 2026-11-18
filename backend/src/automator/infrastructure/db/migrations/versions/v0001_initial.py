from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

INDEXED = {
    "credentials": ("created_at",),
    "channels": ("credential_id",),
    "automations": ("pipeline_type", "created_at"),
    "runs": ("automation_id", "status", "trigger", "created_at"),
    "quota_entries": ("credential_id", "day"),
}


def payload() -> sa.Column[object]:
    return sa.Column("payload", sa.JSON(), nullable=False)


def text(name: str, *, primary_key: bool = False, unique: bool = False) -> sa.Column[str]:
    return sa.Column(name, sa.String(), nullable=False, primary_key=primary_key, unique=unique)


def create_tables() -> None:
    op.create_table("credentials", text("id", primary_key=True), text("created_at"), payload())
    op.create_table(
        "channels",
        text("id", primary_key=True),
        sa.Column("credential_id", sa.String(), sa.ForeignKey("credentials.id"), nullable=False),
        text("youtube_channel_id", unique=True),
        text("connected_at"),
        payload(),
    )
    op.create_table(
        "automations",
        text("id", primary_key=True),
        text("pipeline_type"),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        text("created_at"),
        payload(),
    )
    op.create_table(
        "runs",
        text("id", primary_key=True),
        text("automation_id"),
        text("status"),
        text("trigger"),
        text("created_at"),
        payload(),
    )


def create_settings_tables() -> None:
    op.create_table(
        "provider_configs",
        text("capability", primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
        payload(),
    )
    op.create_table("app_settings", text("id", primary_key=True), payload())
    op.create_table(
        "quota_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        text("credential_id"),
        text("day"),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.UniqueConstraint("credential_id", "day"),
    )


def upgrade() -> None:
    create_tables()
    create_settings_tables()
    for table, columns in INDEXED.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    for table in reversed(
        ("credentials", "channels", "automations", "runs", "provider_configs", "app_settings")
    ):
        op.drop_table(table)
    op.drop_table("quota_entries")
