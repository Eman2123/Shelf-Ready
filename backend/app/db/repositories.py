"""Database repositories. Each method opens its own short session; none is held across a
network call to PayPal."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.contracts import KeyLimits, KeyScope
from app.db.models import (
    AgentKeyRow,
    ApprovalRow,
    AuditLogRow,
    KeySpendRow,
    OrderRow,
    WebhookEventRow,
)
from app.db.session import session_scope
from app.services.keys.store import KeyRecord


def _aware(value: datetime | None) -> datetime | None:
    """SQLite drops tzinfo; everything in this app is UTC."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class SqlKeyRepository:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self.factory = factory

    def load_keys(self) -> list[KeyRecord]:
        with session_scope(self.factory) as s:
            rows = s.scalars(select(AgentKeyRow).order_by(AgentKeyRow.key_id)).all()
            return [
                KeyRecord(
                    key_id=r.key_id,
                    agent_id=r.agent_id,
                    store_id=r.store_id,
                    key_hash=r.key_hash,
                    scopes=tuple(KeyScope(x) for x in r.scopes),
                    limits=KeyLimits.model_validate(r.limits),
                    created_at=_aware(r.created_at),
                    revoked_at=_aware(r.revoked_at),
                )
                for r in rows
            ]

    def save_key(self, record: KeyRecord) -> None:
        with session_scope(self.factory) as s:
            row = s.get(AgentKeyRow, record.key_id) or AgentKeyRow(key_id=record.key_id)
            row.agent_id = record.agent_id
            row.store_id = record.store_id
            row.key_hash = record.key_hash
            row.scopes = [x.value for x in record.scopes]
            row.limits = record.limits.model_dump(mode="json")
            row.created_at = record.created_at
            row.revoked_at = record.revoked_at
            s.add(row)

    def load_spend(self) -> dict[tuple[str, date], int]:
        with session_scope(self.factory) as s:
            return {
                (r.key_id, date.fromisoformat(r.day)): r.cents
                for r in s.scalars(select(KeySpendRow)).all()
            }

    def save_spend(self, key_id: str, day: date, cents: int) -> None:
        with session_scope(self.factory) as s:
            row = s.get(KeySpendRow, (key_id, day.isoformat())) or KeySpendRow(
                key_id=key_id, day=day.isoformat()
            )
            row.cents = cents
            s.add(row)


class OrderRepository:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self.factory = factory

    # --- orders ---------------------------------------------------------------------------
    def insert_order(self, row: OrderRow) -> OrderRow | None:
        """Insert; return None if the idempotency key already exists (caller loads the old one)."""
        try:
            with session_scope(self.factory) as s:
                s.add(row)
        except IntegrityError:
            return None
        return row

    def get(self, order_id: str) -> OrderRow | None:
        with session_scope(self.factory) as s:
            return s.get(OrderRow, order_id)

    def by_idempotency(self, key: str) -> OrderRow | None:
        with session_scope(self.factory) as s:
            return s.scalars(select(OrderRow).where(OrderRow.idempotency_key == key)).first()

    def by_paypal_order(self, paypal_order_id: str) -> OrderRow | None:
        with session_scope(self.factory) as s:
            return s.scalars(
                select(OrderRow).where(OrderRow.paypal_order_id == paypal_order_id)
            ).first()

    def by_authorization(self, authorization_id: str) -> OrderRow | None:
        with session_scope(self.factory) as s:
            return s.scalars(
                select(OrderRow).where(OrderRow.authorization_id == authorization_id)
            ).first()

    def by_capture(self, capture_id: str) -> OrderRow | None:
        with session_scope(self.factory) as s:
            return s.scalars(select(OrderRow).where(OrderRow.capture_id == capture_id)).first()

    def list_orders(self, limit: int = 100) -> list[OrderRow]:
        with session_scope(self.factory) as s:
            stmt = select(OrderRow).order_by(OrderRow.created_at.desc()).limit(limit)
            return list(s.scalars(stmt).all())

    def update(self, order_id: str, **fields: Any) -> OrderRow:
        with session_scope(self.factory) as s:
            row = s.get(OrderRow, order_id)
            if row is None:
                raise KeyError(order_id)
            for k, v in fields.items():
                setattr(row, k, v)
            row.updated_at = datetime.now(UTC)
            s.add(row)
        return row

    def log(self, order_id: str, type_: str, detail: dict[str, Any] | None = None) -> None:
        with session_scope(self.factory) as s:
            s.add(AuditLogRow(order_id=order_id, type=type_, detail=detail or {}))

    def events(self, order_id: str) -> list[AuditLogRow]:
        with session_scope(self.factory) as s:
            stmt = (
                select(AuditLogRow).where(AuditLogRow.order_id == order_id).order_by(AuditLogRow.id)
            )
            return list(s.scalars(stmt).all())

    # --- approvals ------------------------------------------------------------------------
    def insert_approval(self, row: ApprovalRow) -> None:
        with session_scope(self.factory) as s:
            s.add(row)

    def get_approval(self, approval_id: str) -> ApprovalRow | None:
        with session_scope(self.factory) as s:
            return s.get(ApprovalRow, approval_id)

    def approval_for_order(self, order_id: str) -> ApprovalRow | None:
        with session_scope(self.factory) as s:
            return s.scalars(select(ApprovalRow).where(ApprovalRow.order_id == order_id)).first()

    def list_approvals(self, status: str | None = None) -> list[ApprovalRow]:
        with session_scope(self.factory) as s:
            stmt = select(ApprovalRow).order_by(ApprovalRow.created_at.desc())
            if status:
                stmt = stmt.where(ApprovalRow.status == status)
            return list(s.scalars(stmt).all())

    def decide_approval(self, approval_id: str, status: str, now: datetime) -> bool:
        """Move PENDING -> status exactly once. False if it was already decided."""
        with session_scope(self.factory) as s:
            row = s.get(ApprovalRow, approval_id)
            if row is None or row.status != "PENDING":
                return False
            row.status = status
            row.decided_at = now
            s.add(row)
            return True

    # --- webhook events -------------------------------------------------------------------
    def claim_event(
        self, event_id: str, event_type: str, resource_id: str | None, payload: dict
    ) -> bool:
        """True the first time an event id is seen; False for a redelivery."""
        try:
            with session_scope(self.factory) as s:
                s.add(
                    WebhookEventRow(
                        event_id=event_id,
                        event_type=event_type,
                        resource_id=resource_id,
                        payload=payload,
                    )
                )
        except IntegrityError:
            return False
        return True

    def release_event(self, event_id: str) -> None:
        with session_scope(self.factory) as s:
            row = s.get(WebhookEventRow, event_id)
            if row is not None:
                s.delete(row)

    def set_event_outcome(self, event_id: str, outcome: str) -> None:
        with session_scope(self.factory) as s:
            row = s.get(WebhookEventRow, event_id)
            if row is not None:
                row.outcome = outcome
                s.add(row)

    def list_events(self, limit: int = 50) -> list[WebhookEventRow]:
        with session_scope(self.factory) as s:
            stmt = select(WebhookEventRow).order_by(WebhookEventRow.received_at.desc()).limit(limit)
            return list(s.scalars(stmt).all())
