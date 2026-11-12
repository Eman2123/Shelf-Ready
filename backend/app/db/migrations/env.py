"""Alembic environment. DATABASE_URL picks the database; models are the source of truth."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import create_engine

from app.core import env as _env  # noqa: F401  (loads DATABASE_URL from backend/.env)
from app.db.models import Base
from app.db.session import normalize_url

target_metadata = Base.metadata


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Set DATABASE_URL before running migrations.")
    return normalize_url(url)


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
