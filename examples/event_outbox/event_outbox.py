"""Original stdlib reference: HMAC-authenticated, idempotent SQLite event inbox.

Local teaching example, not an internet-ready gateway or exactly-once delivery.
Only signed, bounded payloads enter the persistent inbox; worker leases have
monotonic fencing generations and must be acknowledged before expiration.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Iterator

MAX_BODY = 8192
MAX_AGE = 300
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
_TYPE = re.compile(r"[a-z][a-z0-9_.-]{0,63}\Z")
_TIMESTAMP = re.compile(r"[1-9][0-9]{0,12}\Z")


class EventError(Exception):
    def __init__(self, code: str, http_status: int = 400):
        self.code = code
        self.http_status = http_status
        super().__init__(code)


@dataclass(frozen=True)
class Lease:
    event_id: str
    generation: int
    owner: str
    expires_at: int
    body: bytes


def signature(secret: bytes, raw_body: bytes, timestamp: int) -> str:
    """HMAC is over exact request bytes, not reserialized or reordered JSON."""
    if not isinstance(secret, bytes) or len(secret) < 16:
        raise ValueError("secret_requires_16_bytes")
    if type(timestamp) is not int or timestamp <= 0:
        raise ValueError("invalid_timestamp")
    message = str(timestamp).encode("ascii") + b"." + raw_body
    return "v1=" + hmac.new(secret, message, hashlib.sha256).hexdigest()


def _decode_event(raw: bytes) -> tuple[str, str]:
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_BODY:
        raise EventError("invalid_body_size", 413)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise EventError("duplicate_json_key")
            result[key] = value
        return result
    try:
        item = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except EventError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise EventError("invalid_json") from exc
    if not isinstance(item, dict) or set(item) != {"id", "type", "payload"}:
        raise EventError("invalid_event_shape")
    if not isinstance(item["id"], str) or not _ID.fullmatch(item["id"]):
        raise EventError("invalid_event_id")
    if not isinstance(item["type"], str) or not _TYPE.fullmatch(item["type"]):
        raise EventError("invalid_event_type")
    if not isinstance(item["payload"], dict):
        raise EventError("invalid_payload")
    return item["id"], item["type"]


class EventInbox:
    """SQLite-backed at-least-once local work queue. Public method clocks are injected."""

    def __init__(self, database: Path, secret: bytes, *, max_attempts: int = 3):
        if not isinstance(secret, bytes) or len(secret) < 16:
            raise ValueError("secret_requires_16_bytes")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 20:
            raise ValueError("invalid_attempt_budget")
        self.database = Path(database)
        self.secret = secret
        self.max_attempts = max_attempts
        if str(self.database) == ":memory:":
            raise ValueError("use_file_database")
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS inbox (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    digest TEXT NOT NULL,
                    raw BLOB NOT NULL,
                    received_at INTEGER NOT NULL,
                    state TEXT NOT NULL DEFAULT 'pending'
                        CHECK(state IN ('pending','leased','completed','dead')),
                    generation INTEGER NOT NULL DEFAULT 0,
                    lease_owner TEXT,
                    lease_until INTEGER,
                    completed_at INTEGER
                );
                CREATE INDEX IF NOT EXISTS inbox_ready
                    ON inbox(state, lease_until, received_at);
            """)

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(str(self.database), timeout=5, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("PRAGMA journal_mode=WAL")
            yield db
        finally:
            db.close()

    @staticmethod
    def _now(now: int | None) -> int:
        value = int(time.time()) if now is None else now
        if type(value) is not int or value <= 0:
            raise ValueError("invalid_clock")
        return value

    def ingest(self, raw: bytes, timestamp: str, provided_signature: str,
               *, now: int | None = None) -> dict:
        current = self._now(now)
        if not isinstance(timestamp, str) or not _TIMESTAMP.fullmatch(timestamp):
            raise EventError("unauthorized", 401)
        issued = int(timestamp)
        if abs(current - issued) > MAX_AGE:
            raise EventError("unauthorized", 401)
        if not isinstance(provided_signature, str) or len(provided_signature) != 67:
            raise EventError("unauthorized", 401)
        if not isinstance(raw, bytes) or len(raw) > MAX_BODY:
            raise EventError("invalid_body_size", 413)
        good = signature(self.secret, raw, issued)
        if not hmac.compare_digest(good, provided_signature):
            raise EventError("unauthorized", 401)
        event_id, event_type = _decode_event(raw)
        digest = hashlib.sha256(raw).hexdigest()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute("SELECT digest FROM inbox WHERE event_id=?", (event_id,)).fetchone()
                if row is not None:
                    if row[0] != digest:
                        raise EventError("idempotency_conflict", 409)
                    outcome = "duplicate"
                else:
                    db.execute(
                        "INSERT INTO inbox(event_id,event_type,digest,raw,received_at)"
                        " VALUES(?,?,?,?,?)",
                        (event_id, event_type, digest, raw, current),
                    )
                    outcome = "stored"
                db.commit()
                return {"status": outcome, "event_id": event_id, "digest": digest}
            except BaseException:
                db.rollback()
                raise

    def claim(self, owner: str, *, now: int | None = None,
              ttl: int = 30, limit: int = 1) -> list[Lease]:
        if not isinstance(owner, str) or not _ID.fullmatch(owner):
            raise ValueError("invalid_owner")
        if type(ttl) is not int or not 1 <= ttl <= 300:
            raise ValueError("invalid_ttl")
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError("invalid_limit")
        current = self._now(now)
        leased = []
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                rows = db.execute(
                    "SELECT event_id,raw,generation FROM inbox "
                    "WHERE state='pending' OR (state='leased' AND lease_until<=?) "
                    "ORDER BY received_at,event_id LIMIT ?",
                    (current, limit),
                ).fetchall()
                for event_id, raw, generation in rows:
                    next_generation = generation + 1
                    if next_generation > self.max_attempts:
                        db.execute(
                            "UPDATE inbox SET state='dead', lease_owner=NULL, "
                            "lease_until=NULL WHERE event_id=?",
                            (event_id,),
                        )
                        continue
                    expires = current + ttl
                    db.execute(
                        "UPDATE inbox SET state='leased',generation=?,lease_owner=?,"
                        "lease_until=? WHERE event_id=?",
                        (next_generation, owner, expires, event_id),
                    )
                    leased.append(Lease(event_id, next_generation, owner, expires, bytes(raw)))
                db.commit()
            except BaseException:
                db.rollback()
                raise
        return leased

    def ack(self, lease: Lease, *, now: int | None = None) -> bool:
        """Return False on stale, foreign, expired, or double acknowledgment."""
        if not isinstance(lease, Lease):
            raise ValueError("invalid_lease")
        current = self._now(now)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                result = db.execute(
                    "UPDATE inbox SET state='completed',completed_at=?,"
                    "lease_owner=NULL,lease_until=NULL WHERE event_id=? "
                    "AND state='leased' AND generation=? AND lease_owner=? "
                    "AND lease_until>?",
                    (current, lease.event_id, lease.generation, lease.owner, current),
                )
                db.commit()
                return result.rowcount == 1
            except BaseException:
                db.rollback()
                raise

    def release(self, lease: Lease, *, now: int | None = None) -> bool:
        """Release an active lease; its generation remains consumed."""
        if not isinstance(lease, Lease):
            raise ValueError("invalid_lease")
        current = self._now(now)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                result = db.execute(
                    "UPDATE inbox SET state='pending',lease_owner=NULL,"
                    "lease_until=NULL WHERE event_id=? AND state='leased' "
                    "AND generation=? AND lease_owner=? AND lease_until>?",
                    (lease.event_id, lease.generation, lease.owner, current),
                )
                db.commit()
                return result.rowcount == 1
            except BaseException:
                db.rollback()
                raise

    def receipt(self, event_id: str) -> dict | None:
        if not isinstance(event_id, str) or not _ID.fullmatch(event_id):
            raise ValueError("invalid_event_id")
        with self._db() as db:
            row = db.execute(
                "SELECT event_id,digest,state,generation,completed_at FROM inbox "
                "WHERE event_id=?", (event_id,),
            ).fetchone()
        return None if row is None else dict(zip(
            ("event_id", "digest", "state", "generation", "completed_at"), row,
        ))

    def summary(self) -> dict[str, int]:
        with self._db() as db:
            return dict(db.execute(
                "SELECT state,COUNT(*) FROM inbox GROUP BY state"
            ).fetchall())
