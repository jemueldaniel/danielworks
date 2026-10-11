"""Small single-database job queue; external effects are deliberately out of scope."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterator

MAX_TICK = 2**52
ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")


class Conflict(ValueError):
    """An idempotency key was reused for a different payload or retry policy."""


class LeaseLost(RuntimeError):
    """The job is terminal, the lease expired, or another generation owns it."""


@dataclass(frozen=True)
class Lease:
    tenant: str
    key: str
    generation: int
    attempt: int
    payload: Any


def identifier(value: str) -> str:
    if type(value) is not str or not ID.fullmatch(value):
        raise ValueError("identifier must be 1-64 lowercase ASCII identifier characters")
    return value


def integer(value: int, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("integer outside allowed range")
    return value


def json_text(value: Any) -> str:
    """Reject ambiguous keys, custom objects, excessive nesting and non-JSON numbers."""
    count = 0

    def visit(item: Any, depth: int) -> None:
        nonlocal count
        count += 1
        if count > 512 or depth > 12:
            raise ValueError("JSON complexity limit exceeded")
        kind = type(item)
        if item is None or kind is bool:
            return
        if kind is str:
            if len(item) > 4096:
                raise ValueError("JSON string limit exceeded")
        elif kind is int:
            integer(item, -(2**53 - 1), 2**53 - 1)
        elif kind is float:
            # json.dumps(allow_nan=False) below rejects NaN and infinities.
            pass
        elif kind is list:
            for child in item:
                visit(child, depth + 1)
        elif kind is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise ValueError("JSON object keys must be strings")
                visit(key, depth + 1)
                visit(child, depth + 1)
        else:
            raise ValueError("only plain JSON values are accepted")

    visit(value, 0)
    encoded = json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > 4096:
        raise ValueError("JSON byte limit exceeded")
    return encoded


class JobQueue:
    """One connection per thread. Tenant IDs partition data; they are not authentication."""

    def __init__(self, path: str | Path):
        self._db = sqlite3.connect(path, timeout=0.1, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        try:
            self._db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                tenant TEXT NOT NULL,
                key TEXT NOT NULL,
                payload TEXT NOT NULL,
                max_attempts INTEGER NOT NULL CHECK (max_attempts BETWEEN 1 AND 10),
                attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0 AND attempts <= max_attempts),
                generation INTEGER NOT NULL DEFAULT 0,
                state TEXT NOT NULL CHECK (state IN ('pending','running','done','failed','cancelled')),
                ready_at INTEGER NOT NULL,
                leased_at INTEGER,
                lease_until INTEGER,
                result TEXT,
                PRIMARY KEY (tenant, key),
                CHECK ((state = 'running' AND leased_at IS NOT NULL AND lease_until > leased_at)
                    OR (state <> 'running' AND leased_at IS NULL AND lease_until IS NULL))
            )""")
        except BaseException:
            self._db.close()
            raise

    def __enter__(self) -> JobQueue:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        self._db.close()

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        # Reserve the sole SQLite writer before selecting a candidate job.
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self._db.execute("COMMIT")
        except BaseException:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            raise

    def submit(self, tenant: str, key: str, payload: Any, *, now: int = 0, max_attempts: int = 3) -> str:
        tenant, key = identifier(tenant), identifier(key)
        now = integer(now, 0, MAX_TICK)
        max_attempts = integer(max_attempts, 1, 10)
        encoded = json_text(payload)
        with self._transaction():
            row = self._db.execute("SELECT payload, max_attempts, state FROM jobs WHERE tenant=? AND key=?", (tenant, key)).fetchone()
            if row is not None:
                if row["payload"] != encoded or row["max_attempts"] != max_attempts:
                    raise Conflict("key already binds a different request")
                return row["state"]
            self._db.execute("INSERT INTO jobs (tenant,key,payload,max_attempts,state,ready_at) VALUES (?,?,?,?,'pending',?)", (tenant, key, encoded, max_attempts, now))
        return "pending"

    def claim(self, tenant: str, *, now: int, lease_ticks: int = 5) -> Lease | None:
        tenant = identifier(tenant)
        now = integer(now, 0, MAX_TICK)
        until = integer(now + integer(lease_ticks, 1, 1_000_000), 0, MAX_TICK)
        with self._transaction():
            self._db.execute("""UPDATE jobs SET
                state=CASE WHEN attempts >= max_attempts THEN 'failed' ELSE 'pending' END,
                ready_at=?, leased_at=NULL, lease_until=NULL
                WHERE tenant=? AND state='running' AND lease_until<=?""", (now, tenant, now))
            row = self._db.execute("""SELECT * FROM jobs WHERE tenant=? AND state='pending'
                AND ready_at<=? AND attempts<max_attempts ORDER BY ready_at, key LIMIT 1""", (tenant, now)).fetchone()
            if row is None:
                return None
            generation, attempt = row["generation"] + 1, row["attempts"] + 1
            self._db.execute("""UPDATE jobs SET state='running', generation=?, attempts=?, leased_at=?, lease_until=?
                WHERE tenant=? AND key=?""", (generation, attempt, now, until, tenant, row["key"]))
            return Lease(tenant, row["key"], generation, attempt, json.loads(row["payload"]))

    def _owned(self, lease: Lease, now: int) -> sqlite3.Row:
        if not isinstance(lease, Lease):
            raise ValueError("a Lease is required")
        integer(lease.generation, 1, MAX_TICK)
        row = self._db.execute("""SELECT * FROM jobs WHERE tenant=? AND key=? AND generation=?
            AND state='running' AND leased_at<=? AND lease_until>?""",
            (identifier(lease.tenant), identifier(lease.key), lease.generation, now, now)).fetchone()
        if row is None:
            raise LeaseLost("lease is no longer current")
        return row

    def complete(self, lease: Lease, result: Any, *, now: int) -> None:
        now, encoded = integer(now, 0, MAX_TICK), json_text(result)
        with self._transaction():
            self._owned(lease, now)
            self._db.execute("""UPDATE jobs SET state='done', result=?, leased_at=NULL, lease_until=NULL
                WHERE tenant=? AND key=?""", (encoded, lease.tenant, lease.key))

    def retry(self, lease: Lease, *, now: int, delay_ticks: int = 0) -> str:
        now = integer(now, 0, MAX_TICK)
        ready = integer(now + integer(delay_ticks, 0, 1_000_000), 0, MAX_TICK)
        with self._transaction():
            row = self._owned(lease, now)
            state = "failed" if row["attempts"] >= row["max_attempts"] else "pending"
            self._db.execute("""UPDATE jobs SET state=?, ready_at=?, leased_at=NULL, lease_until=NULL
                WHERE tenant=? AND key=?""", (state, ready, lease.tenant, lease.key))
        return state

    def cancel(self, tenant: str, key: str) -> bool:
        tenant, key = identifier(tenant), identifier(key)
        with self._transaction():
            cursor = self._db.execute("""UPDATE jobs SET state='cancelled', generation=generation+1,
                leased_at=NULL, lease_until=NULL WHERE tenant=? AND key=? AND state IN ('pending','running')""", (tenant, key))
        return cursor.rowcount == 1

    def inspect(self, tenant: str, key: str) -> dict[str, Any] | None:
        row = self._db.execute("SELECT * FROM jobs WHERE tenant=? AND key=?", (identifier(tenant), identifier(key))).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        result["result"] = json.loads(result["result"]) if result["result"] is not None else None
        return result
