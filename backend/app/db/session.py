"""Database engine and session factory.

DATABASE_URL picks the database (Postgres in production, SQLite file for local dev and tests).
Providers often hand out `postgres://` or `postgresql://`; both are rewritten to the psycopg
driver this project installs.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_URL = "sqlite://"  # in-memory unless DATABASE_URL is set


def normalize_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def make_engine(url: str | None = None) -> Engine:
    url = normalize_url(url or os.environ.get("DATABASE_URL") or DEFAULT_URL)
    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url == "sqlite://":
            kwargs["poolclass"] = StaticPool  # one shared connection so tables survive
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
