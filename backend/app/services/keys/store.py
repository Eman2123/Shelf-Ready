"""Per-agent API keys (PRD M7).

Rules this module enforces:
- A raw key is returned once, at creation. Only its SHA-256 hash is stored.
- A revoked key fails on the very next verify() call (kill switch, no cache).
- Expired keys fail. Keys over requests_per_minute fail with RATE_LIMITED.
- Spend per agent per UTC day is tracked here, so the policy engine can enforce the agent budget.

In-memory on purpose: the Postgres repository comes with the DB layer. The public surface
(create_key, verify, revoke, record_spend) stays the same when it is swapped in.
"""

from __future__ import annotations

import hashlib
import secrets
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from typing import Protocol

from app.contracts import (
    KeyFailureReason,
    KeyLimits,
    KeyRejected,
    KeyScope,
    KeyVerification,
    KeyVerified,
    VerifiedAgent,
)

RATE_WINDOW = timedelta(minutes=1)
KEY_PREFIX = "srk_"


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


@dataclass(frozen=True)
class KeyRecord:
    key_id: str
    agent_id: str
    store_id: str
    key_hash: str
    scopes: tuple[KeyScope, ...]
    limits: KeyLimits
    created_at: datetime
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class IssuedKey:
    """Returned once by create_key. The raw key is never stored and cannot be read again."""

    raw_key: str
    record: KeyRecord


class KeyRepository(Protocol):
    """Where keys survive a restart. The in-memory dicts stay the working copy."""

    def load_keys(self) -> list[KeyRecord]: ...

    def save_key(self, record: KeyRecord) -> None: ...

    def load_spend(self) -> dict[tuple[str, date], int]: ...

    def save_spend(self, key_id: str, day: date, cents: int) -> None: ...


class KeyStore:
    def __init__(
        self,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        repository: KeyRepository | None = None,
    ) -> None:
        self.clock = clock
        self.repository = repository
        self._by_hash: dict[str, KeyRecord] = {}
        self._by_id: dict[str, KeyRecord] = {}
        self._requests: dict[str, deque[datetime]] = defaultdict(deque)
        self._spent: dict[tuple[str, date], int] = defaultdict(int)
        self._counter = 0
        if repository is not None:
            for record in repository.load_keys():
                self._by_hash[record.key_hash] = record
                self._by_id[record.key_id] = record
                self._counter = max(self._counter, int(record.key_id.split("_")[-1]))
            for k, cents in repository.load_spend().items():
                self._spent[k] = cents

    # --- lifecycle --------------------------------------------------------------------
    def create_key(
        self,
        agent_id: str,
        store_id: str,
        scopes: list[KeyScope],
        limits: KeyLimits,
    ) -> IssuedKey:
        if not scopes:
            raise ValueError("a key needs at least one scope")
        self._counter += 1
        raw = KEY_PREFIX + secrets.token_urlsafe(32)
        record = KeyRecord(
            key_id=f"key_{self._counter:04d}",
            agent_id=agent_id,
            store_id=store_id,
            key_hash=hash_key(raw),
            scopes=tuple(dict.fromkeys(scopes)),
            limits=limits,
            created_at=self.clock(),
        )
        self._by_hash[record.key_hash] = record
        self._by_id[record.key_id] = record
        if self.repository is not None:
            self.repository.save_key(record)
        return IssuedKey(raw_key=raw, record=record)

    def revoke(self, key_id: str) -> KeyRecord:
        """Kill switch. Takes effect on the next verify() call."""
        record = self._by_id.get(key_id)
        if record is None:
            raise KeyError(key_id)
        revoked = replace(record, revoked_at=record.revoked_at or self.clock())
        self._by_hash[record.key_hash] = revoked
        self._by_id[key_id] = revoked
        if self.repository is not None:
            self.repository.save_key(revoked)
        return revoked

    def get(self, key_id: str) -> KeyRecord | None:
        return self._by_id.get(key_id)

    def list_keys(self) -> list[KeyRecord]:
        """Every key record, oldest first. Records hold the hash only, never the raw key."""
        return list(self._by_id.values())

    # --- verification -----------------------------------------------------------------
    def identify(self, raw_key: str) -> KeyVerification:
        """Who is this key, right now? Same revoke and expiry checks as verify(), but it does
        NOT count against the rate limit. The guarded order flow calls it after verify()."""
        if not raw_key.strip():
            return KeyRejected(reason=KeyFailureReason.KEY_UNKNOWN)
        record = self._by_hash.get(hash_key(raw_key))
        if record is None:
            return KeyRejected(reason=KeyFailureReason.KEY_UNKNOWN)
        now = self.clock()
        if record.revoked_at is not None:
            return KeyRejected(reason=KeyFailureReason.KEY_REVOKED)
        if record.limits.expires_at is not None and now >= record.limits.expires_at:
            return KeyRejected(reason=KeyFailureReason.KEY_EXPIRED)
        return self._verified(record)

    @staticmethod
    def _verified(record: KeyRecord) -> KeyVerified:
        return KeyVerified(
            agent=VerifiedAgent(
                agent_id=record.agent_id,
                key_id=record.key_id,
                store_id=record.store_id,
                scopes=list(record.scopes),
                limits=record.limits,
            )
        )

    def verify(self, raw_key: str) -> KeyVerification:
        """Identity check on every order call. Matches StoreService's verify_key signature."""
        identified = self.identify(raw_key)
        if not identified.ok:
            return identified
        record = self._by_id[identified.agent.key_id]
        now = self.clock()
        window = self._requests[record.key_id]
        while window and now - window[0] >= RATE_WINDOW:
            window.popleft()
        if len(window) >= record.limits.requests_per_minute:
            return KeyRejected(reason=KeyFailureReason.RATE_LIMITED)
        window.append(now)
        return identified

    # --- spend ------------------------------------------------------------------------
    def spent_today(self, key_id: str) -> int:
        return self._spent[(key_id, self.clock().date())]

    def record_spend(self, key_id: str, cents: int) -> int:
        if cents < 0:
            raise ValueError("spend cannot be negative")
        key = (key_id, self.clock().date())
        self._spent[key] += cents
        if self.repository is not None:
            self.repository.save_spend(key_id, key[1], self._spent[key])
        return self._spent[key]
