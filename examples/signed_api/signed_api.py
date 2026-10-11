"""Original localhost signed-request gateway with atomic SQLite replay limits.

Educational HMAC-SHA256 request authentication (shared key possession only).
No TLS, account enrollment, OAuth, KMS, key rotation, production IAM or cloud.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
from pathlib import Path
import re
import secrets
import sqlite3
import time
from typing import Callable

_ID = re.compile(r"[a-z][a-z0-9_-]{1,47}\Z")
_NONCE = re.compile(r"[A-Za-z0-9_-]{16,64}\Z")
_SIGNATURE = re.compile(r"[0-9a-f]{64}\Z")
_PATH = re.compile(r"/[a-z0-9/_-]{1,120}\Z")
MAX_BODY = 65536
PATH = "/v1/accept"
METHODS = frozenset(("POST", "PUT", "PATCH", "DELETE"))


class RequestError(ValueError):
    """A stable symbolic failure without credentials or request content."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fail(code: str):
    raise RequestError(code)


def _identifier(value: object, field: str) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        _fail("invalid_" + field)
    return value


@dataclass(frozen=True)
class Credential:
    key_id: str
    tenant: str
    secret: bytes


def credential(key_id: str, tenant: str, secret: bytes) -> Credential:
    _identifier(key_id, "key_id")
    _identifier(tenant, "tenant")
    if type(secret) is not bytes or not 32 <= len(secret) <= 128:
        _fail("invalid_secret")
    return Credential(key_id, tenant, secret)


@dataclass(frozen=True)
class Envelope:
    key_id: str
    tenant: str
    method: str
    path: str
    timestamp: int
    nonce: str
    signature: str
    body: bytes


def _normalize(key_id: str, tenant: str, method: str, path: str,
               timestamp: int, nonce: str, body: bytes) -> bytes:
    _identifier(key_id, "key_id")
    _identifier(tenant, "tenant")
    if type(method) is not str or method not in METHODS:
        _fail("invalid_method")
    if type(path) is not str or not _PATH.fullmatch(path) or "//" in path:
        _fail("invalid_path")
    if type(timestamp) is not int or not 1 <= timestamp <= 9999999999:
        _fail("invalid_timestamp")
    if type(nonce) is not str or not _NONCE.fullmatch(nonce):
        _fail("invalid_nonce")
    if type(body) is not bytes or len(body) > MAX_BODY:
        _fail("invalid_body")
    message = ["PUBLIC-SIGNED-API-v1", key_id, tenant, method, path,
               timestamp, nonce, sha256(body).hexdigest()]
    return json.dumps(message, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sign(key: Credential, method: str, path: str, body: bytes,
         *, timestamp: int, nonce: str | None = None) -> Envelope:
    if type(key) is not Credential:
        _fail("invalid_credential")
    if nonce is None:
        nonce = secrets.token_urlsafe(18)
    canonical = _normalize(key.key_id, key.tenant, method, path, timestamp, nonce, body)
    signature = hmac.new(key.secret, canonical, "sha256").hexdigest()
    return Envelope(key.key_id, key.tenant, method, path, timestamp, nonce,
                    signature, body)


class Verifier:
    """Single-node durable replay detection; key scopes are caller-configured.

    Each successful signature burns one nonce before returning success.
    All database decisions are serialized in BEGIN IMMEDIATE. This is NOT
    an externally audited auth service or a distributed replay barrier.
    """

    def __init__(self, database: str | Path, keys: list[Credential], *,
                 clock: Callable[[], float] = time.time,
                 skew_seconds: int = 60, window_seconds: int = 60,
                 limit: int = 25):
        if not isinstance(database, (str, Path)):
            _fail("invalid_database")
        self.database = Path(database).absolute()
        if not self.database.parent.is_dir():
            _fail("invalid_database_parent")
        if type(keys) is not list or not keys or len(keys) > 32:
            _fail("invalid_credentials")
        credentials = {}
        for item in keys:
            if type(item) is not Credential:
                _fail("invalid_credentials")
            valid = credential(item.key_id, item.tenant, item.secret)
            if valid.key_id in credentials:
                _fail("duplicate_key_id")
            credentials[valid.key_id] = valid
        if not callable(clock):
            _fail("invalid_clock")
        if type(skew_seconds) is not int or not 1 <= skew_seconds <= 300:
            _fail("invalid_skew")
        if type(window_seconds) is not int or not 1 <= window_seconds <= 3600:
            _fail("invalid_window")
        if type(limit) is not int or not 1 <= limit <= 1000:
            _fail("invalid_limit")
        self.keys = credentials
        self.clock = clock
        self.skew = skew_seconds
        self.window = window_seconds
        self.limit = limit
        # Nonces live longer than their maximum accepted timestamp window.
        self.retention = 2 * self.skew + self.window + 5
        con = self._connect()
        try:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS seen_requests (
                    key_id TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    seen_at REAL NOT NULL,
                    PRIMARY KEY(key_id, nonce)
                );
                CREATE INDEX IF NOT EXISTS seen_by_time
                    ON seen_requests(seen_at);
            """)
        finally:
            con.close()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.database), timeout=10, isolation_level=None)
        con.execute("PRAGMA busy_timeout=10000")
        return con

    def verify(self, request: Envelope) -> dict:
        if type(request) is not Envelope:
            _fail("invalid_envelope")
        canonical = _normalize(request.key_id, request.tenant, request.method,
                               request.path, request.timestamp, request.nonce,
                               request.body)
        if type(request.signature) is not str or not _SIGNATURE.fullmatch(request.signature):
            _fail("invalid_signature")
        key = self.keys.get(request.key_id)
        if key is None or key.tenant != request.tenant:
            _fail("unauthorized")
        expected = hmac.new(key.secret, canonical, "sha256").hexdigest()
        if not hmac.compare_digest(expected, request.signature):
            _fail("unauthorized")
        now = float(self.clock())
        if not (0 < now < 10**10) or abs(now - request.timestamp) > self.skew:
            _fail("timestamp_out_of_window")
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("DELETE FROM seen_requests WHERE seen_at < ?",
                        (now - self.retention,))
            exists = con.execute(
                "SELECT 1 FROM seen_requests WHERE key_id=? AND nonce=?",
                (request.key_id, request.nonce)).fetchone()
            if exists:
                _fail("replay")
            current = con.execute(
                "SELECT COUNT(*) FROM seen_requests WHERE key_id=? AND seen_at > ?",
                (request.key_id, now - self.window)).fetchone()[0]
            if current >= self.limit:
                _fail("rate_limited")
            con.execute(
                "INSERT INTO seen_requests(key_id,nonce,seen_at) VALUES(?,?,?)",
                (request.key_id, request.nonce, now))
            con.commit()
        except sqlite3.Error as exc:
            if con.in_transaction:
                con.rollback()
            raise RequestError("storage_unavailable") from exc
        except Exception:
            if con.in_transaction:
                con.rollback()
            raise
        finally:
            con.close()
        return {"status": "ACCEPTED", "tenant": key.tenant,
                "body_sha256": sha256(request.body).hexdigest(),
                "scope": "shared-key local authentication, not cloud IAM"}


def loopback_server(verifier: Verifier) -> ThreadingHTTPServer:
    """Tests only: never bind this plaintext transport to an external host."""
    if type(verifier) is not Verifier:
        _fail("invalid_verifier")

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format, *args):
            # Do not log plaintext payloads, key IDs, or signature values.
            return

        def send_json(self, code: int, data: dict) -> None:
            payload = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            self.wfile.write(payload)

        def early_error(self, code: int, payload: dict) -> None:
            # On Windows an unread small declared request body can cause a
            # TCP reset that hides the intended bounded HTTP rejection.
            # Drain only a strictly bounded, unambiguous fixed-length body.
            values = self.headers.get_all("Content-Length", [])
            if (self.headers.get("Transfer-Encoding") is None
                    and len(values) == 1 and values[0].isdigit()
                    and len(values[0]) <= 6):
                count = int(values[0])
                if count <= MAX_BODY + 1:
                    try:
                        self.connection.settimeout(2)
                        self.rfile.read(count)
                    except (TimeoutError, OSError):
                        pass
            return self.send_json(code, payload)

        def do_POST(self):
            if self.path != PATH:
                return self.early_error(404, {"status": "NOT_FOUND"})
            if self.headers.get("Transfer-Encoding") is not None:
                return self.send_json(400, {"status": "INVALID_BODY"})
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or not lengths[0].isdigit() or len(lengths[0]) > 6:
                return self.send_json(400, {"status": "INVALID_LENGTH"})
            amount = int(lengths[0])
            if amount > MAX_BODY:
                return self.early_error(413, {"status": "BODY_TOO_LARGE"})
            needed = ("X-Public-Key", "X-Public-Tenant", "X-Public-Time",
                      "X-Public-Nonce", "X-Public-Signature")
            if any(len(self.headers.get_all(name, [])) != 1 for name in needed):
                return self.early_error(400, {"status": "INVALID_HEADERS"})
            time_raw = self.headers["X-Public-Time"]
            if not time_raw.isascii() or not time_raw.isdigit() or len(time_raw) > 10:
                return self.early_error(400, {"status": "INVALID_TIME"})
            self.connection.settimeout(5)
            try:
                body = self.rfile.read(amount)
                if len(body) != amount:
                    return self.send_json(400, {"status": "INCOMPLETE_BODY"})
                envelope = Envelope(
                    self.headers["X-Public-Key"], self.headers["X-Public-Tenant"],
                    "POST", PATH, int(time_raw), self.headers["X-Public-Nonce"],
                    self.headers["X-Public-Signature"], body)
                result = verifier.verify(envelope)
                return self.send_json(200, result)
            except RequestError as exc:
                status = 409 if exc.code == "replay" else (
                    429 if exc.code == "rate_limited" else 401)
                return self.send_json(status, {"status": exc.code.upper()})
            except (TimeoutError, OSError):
                self.close_connection = True

        def do_GET(self):
            return self.send_json(405, {"status": "METHOD_NOT_ALLOWED"})

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)
