"""Alembic environment.

Used programmatically by postulo.db.session.run_migrations (connection passed in
config.attributes) and from the command line for new revisions:

    uv run alembic -c backend/postulo/db/alembic.ini revision --autogenerate -m "..."
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import Connection, create_engine
from sqlmodel import SQLModel

import postulo.db.models  # noqa: F401  (registers tables on SQLModel.metadata)
from postulo import config as postulo_config

target_metadata = SQLModel.metadata


def _configure(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # SQLite cannot ALTER most things in place
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _configure(connection)
        return
    url = context.config.get_main_option("sqlalchemy.url") or postulo_config.database_url()
    engine = create_engine(url)
    with engine.connect() as conn:
        _configure(conn)
        conn.commit()


if context.is_offline_mode():
    context.configure(
        url=context.config.get_main_option("sqlalchemy.url") or postulo_config.database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()
