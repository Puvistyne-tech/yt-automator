from __future__ import annotations

from alembic import context
from sqlalchemy import Connection, create_engine

from autotube.infrastructure.db.tables import METADATA


def run_with(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=METADATA,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations() -> None:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        run_with(connection)
        return
    url = context.config.get_main_option("sqlalchemy.url") or ""
    with create_engine(url).connect() as fresh:
        run_with(fresh)


run_migrations()
