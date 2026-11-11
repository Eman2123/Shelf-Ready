"""Tables. Money is integer cents. JSON columns hold small structured blobs (items, limits)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class AgentKeyRow(Base):
    __tablename__ = "agent_keys"

    key_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    store_id: Mapped[str] = mapped_column(String(64))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # SHA-256 only
    scopes: Mapped[list] = mapped_column(JSON)
    limits: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KeySpendRow(Base):
    __tablename__ = "key_spend"

    key_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    day: Mapped[str] = mapped_column(String(10), primary_key=True)  # UTC date, YYYY-MM-DD
    cents: Mapped[int] = mapped_column(BigInteger, default=0)


class OrderRow(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    agent_id: Mapped[str] = mapped_column(String(64))
    key_id: Mapped[str] = mapped_column(String(32))
    store_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    total_cents: Mapped[int] = mapped_column(BigInteger)
    items: Mapped[list] = mapped_column(JSON)
    decision: Mapped[dict] = mapped_column(JSON)
    paypal_order_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    authorization_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    capture_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    refund_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    seller_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    failure: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ApprovalRow(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    status: Mapped[str] = mapped_column(String(12), index=True)  # PENDING/APPROVED/REJECTED/EXPIRED
    reason: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WebhookEventRow(Base):
    """One row per PayPal event id. The primary key is what makes redelivery harmless."""

    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    outcome: Mapped[str] = mapped_column(String(32), default="RECEIVED")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLogRow(Base):
    """Append-only log of money-path transitions (who/what/when), shown on the Orders screen."""

    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(40), index=True)
    type: Mapped[str] = mapped_column(String(40))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
