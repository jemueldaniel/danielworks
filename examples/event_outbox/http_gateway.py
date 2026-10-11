"""Loopback-only HTTP adapter for the original durable signed event example."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re

from event_outbox import EventInbox, EventError, MAX_BODY


def make_server(inbox: EventInbox, *, port: int = 0) -> ThreadingHTTPServer:
    if not isinstance(inbox, EventInbox):
        raise ValueError("invalid_inbox")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("invalid_port")

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "PublicReference/1.0"
        sys_version = ""

        def log_message(self, *args):
            # Never log signed payloads, signatures or bearer-like headers.
            pass

        def handle_expect_100(self):
            self._respond(417, {"error": "expect_not_supported"})
            return False

        def _respond(self, status: int, body: dict):
            raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(raw)
            self.close_connection = True

        def _unique(self, key: str) -> str | None:
            values = self.headers.get_all(key, [])
            return values[0] if len(values) == 1 else None

        def do_GET(self):
            if self.path == "/health":
                self._respond(200, {"status": "ok", "scope": "loopback_only"})
            else:
                self._respond(404, {"error": "not_found"})

        def do_POST(self):
            if self.path != "/events":
                self._respond(404, {"error": "not_found"})
                return
            self.connection.settimeout(5)
            if self.headers.get_all("Transfer-Encoding"):
                self._respond(400, {"error": "unsupported_transfer_encoding"})
                return
            lengths = self.headers.get_all("Content-Length", [])
            if not lengths:
                self._respond(411, {"error": "length_required"})
                return
            if len(lengths) != 1 or not re.fullmatch(r"[1-9][0-9]{0,5}", lengths[0]):
                self._respond(400, {"error": "invalid_content_length"})
                return
            size = int(lengths[0])
            if size > MAX_BODY:
                self._respond(413, {"error": "body_too_large"})
                return
            timestamp = self._unique("X-Event-Timestamp")
            provided = self._unique("X-Event-Signature")
            if timestamp is None or provided is None:
                self._respond(401, {"error": "unauthorized"})
                return
            try:
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise ValueError("truncated_body")
                result = inbox.ingest(raw, timestamp, provided)
            except EventError as exc:
                self._respond(exc.http_status, {"error": exc.code})
            except (ValueError, TimeoutError, OSError):
                self._respond(400, {"error": "invalid_body"})
            else:
                self._respond(202 if result["status"] == "stored" else 200, result)

    class LocalServer(ThreadingHTTPServer):
        daemon_threads = True
        request_queue_size = 16
        allow_reuse_address = True

    return LocalServer(("127.0.0.1", port), Handler)
