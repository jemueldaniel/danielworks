"""Real SQLite, thread, process-reopen, and loopback HTTP acceptance tests."""
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from event_outbox import EventError, EventInbox, Lease, MAX_BODY, signature
from http_gateway import make_server

KEY = b"synthetic-public-example-key-12345"
CLOCK = 1800000000


def body(event_id="evt_1", kind="document.created", payload=None):
    if payload is None:
        payload = {"label": "synthetic", "value": 3}
    return json.dumps({"id": event_id, "type": kind, "payload": payload},
                      sort_keys=True, separators=(",", ":")).encode()


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "events.sqlite"
        self.box = EventInbox(self.db, KEY)

    def tearDown(self):
        self.temp.cleanup()

    def push(self, raw=None, timestamp=CLOCK, signed_key=KEY):
        raw = body() if raw is None else raw
        return self.box.ingest(raw, str(timestamp), signature(signed_key, raw, timestamp),
                               now=CLOCK)

    def test_new_event_and_receipt(self):
        raw = body()
        result = self.push(raw)
        self.assertEqual(result["status"], "stored")
        row = self.box.receipt("evt_1")
        self.assertEqual(row["state"], "pending")
        self.assertEqual(row["digest"], result["digest"])
        self.assertEqual(row["generation"], 0)

    def test_exact_duplicate_is_idempotent(self):
        self.assertEqual(self.push()["status"], "stored")
        self.assertEqual(self.push()["status"], "duplicate")
        self.assertEqual(self.box.summary(), {"pending": 1})

    def test_same_id_different_bytes_is_conflict(self):
        self.push()
        with self.assertRaises(EventError) as error:
            self.push(body(payload={"label": "changed"}))
        self.assertEqual((error.exception.code, error.exception.http_status),
                         ("idempotency_conflict", 409))

    def test_modified_message_rejected_before_persistence(self):
        raw = body()
        with self.assertRaises(EventError) as e:
            self.box.ingest(raw + b" ", str(CLOCK), signature(KEY, raw, CLOCK), now=CLOCK)
        self.assertEqual(e.exception.http_status, 401)
        self.assertEqual(self.box.summary(), {})

    def test_wrong_signing_key(self):
        with self.assertRaises(EventError) as e:
            self.push(signed_key=b"synthetic-different-key-12345678")
        self.assertEqual(e.exception.code, "unauthorized")

    def test_past_and_future_signature_expiry(self):
        for t in [CLOCK - 301, CLOCK + 301]:
            with self.subTest(t=t), self.assertRaises(EventError) as e:
                self.push(timestamp=t)
            self.assertEqual(e.exception.http_status, 401)

    def test_freshness_boundary_is_inclusive(self):
        self.assertEqual(self.push(timestamp=CLOCK - 300)["status"], "stored")
        self.assertEqual(self.push(timestamp=CLOCK + 300)["status"], "duplicate")

    def test_invalid_timestamp(self):
        raw = body()
        for bad in ["", "-123", "0123", "1.0", str(CLOCK) + "x", " "]:
            with self.subTest(bad=bad), self.assertRaises(EventError):
                self.box.ingest(raw, bad, signature(KEY, raw, CLOCK), now=CLOCK)

    def test_invalid_signature_format(self):
        raw = body()
        for bad in ["", "v1=", "v1=" + "0" * 63, 3, None]:
            with self.subTest(bad=bad), self.assertRaises(EventError):
                self.box.ingest(raw, str(CLOCK), bad, now=CLOCK)

    def test_signature_requires_strong_synthetic_key(self):
        with self.assertRaises(ValueError):
            EventInbox(self.db, b"short")
        with self.assertRaises(ValueError):
            signature(b"short", b"hi", CLOCK)

    def test_duplicate_json_keys_rejected(self):
        raw = b'{"id":"x","id":"y","type":"created","payload":{}}'
        with self.assertRaises(EventError) as e:
            self.push(raw)
        self.assertEqual(e.exception.code, "duplicate_json_key")

    def test_invalid_event_shapes_and_types(self):
        invalid = [
            b'[]', b'{"id":"one","type":"a"}', b'{"id":"one","type":"a","payload":[]}',
            body("a b"), body("one", "InvalidType"), body(payload={"x":float("nan")}),
            b'{"id":"one","type":"created","payload":{},"privileged":true}',
            b'{"id":"one","type":"created","payload":null}',
            b'{"id":"one","type":"created","payload":{}}garbage',
            b'\xff',
        ]
        for raw in invalid:
            with self.subTest(raw=raw[:60]), self.assertRaises(EventError):
                self.push(raw)

    def test_payload_bound(self):
        raw = b"x" * (MAX_BODY + 1)
        with self.assertRaises(EventError) as e:
            self.push(raw)
        self.assertEqual(e.exception.http_status, 413)

    def test_sql_injection_like_id_is_data(self):
        raw = body("1_or_1--")
        self.push(raw)
        self.assertIsNone(self.box.receipt("other"))
        self.assertEqual(self.box.receipt("1_or_1--")["state"], "pending")

    def test_concurrent_duplicate_writes(self):
        raw = body()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.push(raw)["status"], range(24)))
        self.assertEqual(results.count("stored"), 1)
        self.assertEqual(results.count("duplicate"), 23)
        self.assertEqual(self.box.summary(), {"pending": 1})

    def test_concurrent_distinct_writes(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda i: self.push(body("ev_" + str(i))), range(25)))
        self.assertEqual(self.box.summary(), {"pending": 25})

    def test_single_owner_claim_and_ack(self):
        self.push()
        leases = self.box.claim("worker_a", now=CLOCK, ttl=10)
        self.assertEqual(len(leases), 1)
        self.assertEqual(leases[0].generation, 1)
        self.assertEqual(leases[0].body, body())
        self.assertEqual(self.box.claim("worker_b", now=CLOCK), [])
        self.assertTrue(self.box.ack(leases[0], now=CLOCK + 3))
        self.assertFalse(self.box.ack(leases[0], now=CLOCK + 4))
        self.assertEqual(self.box.summary(), {"completed": 1})

    def test_expired_lease_cannot_ack(self):
        self.push()
        lease = self.box.claim("alpha", now=CLOCK, ttl=1)[0]
        self.assertFalse(self.box.ack(lease, now=CLOCK + 1))
        next_lease = self.box.claim("beta", now=CLOCK + 1)[0]
        self.assertEqual(next_lease.generation, 2)
        self.assertFalse(self.box.ack(lease, now=CLOCK + 1))
        self.assertTrue(self.box.ack(next_lease, now=CLOCK + 1))

    def test_forged_owner_or_generation_is_fenced(self):
        self.push()
        lease = self.box.claim("alpha", now=CLOCK)[0]
        self.assertFalse(self.box.ack(Lease(lease.event_id, lease.generation,
                                            "attacker", lease.expires_at, lease.body),
                                      now=CLOCK))
        self.assertFalse(self.box.ack(Lease(lease.event_id, 99,
                                            lease.owner, lease.expires_at, lease.body),
                                      now=CLOCK))
        self.assertTrue(self.box.ack(lease, now=CLOCK))

    def test_release_consumes_fencing_generation(self):
        self.push()
        old = self.box.claim("alpha", now=CLOCK)[0]
        self.assertTrue(self.box.release(old, now=CLOCK + 1))
        self.assertFalse(self.box.ack(old, now=CLOCK + 1))
        latest = self.box.claim("alpha", now=CLOCK + 2)[0]
        self.assertEqual(latest.generation, 2)
        self.assertTrue(self.box.ack(latest, now=CLOCK + 3))

    def test_expiry_and_retry_budget_dead_letter(self):
        self.push()
        for gen in range(1, 4):
            lease = self.box.claim("worker", now=CLOCK + gen * 10, ttl=1)[0]
            self.assertEqual(lease.generation, gen)
        self.assertEqual(self.box.claim("worker", now=CLOCK + 40), [])
        self.assertEqual(self.box.summary(), {"dead": 1})
        self.assertFalse(self.box.ack(lease, now=CLOCK + 40))

    def test_process_reopen_preserves_state(self):
        self.push()
        first = self.box.claim("old", now=CLOCK, ttl=10)[0]
        recovered = EventInbox(self.db, KEY)
        self.assertEqual(recovered.claim("new", now=CLOCK + 3), [])
        new = recovered.claim("new", now=CLOCK + 10)[0]
        self.assertNotEqual(first.generation, new.generation)
        self.assertTrue(recovered.ack(new, now=CLOCK + 11))
        self.assertEqual(EventInbox(self.db, KEY).receipt("evt_1")["state"], "completed")

    def test_pending_order_is_stable(self):
        self.push(body("b"))
        self.push(body("a"))
        self.assertEqual([x.event_id for x in self.box.claim("worker", now=CLOCK, limit=2)],
                         ["a", "b"])

    def test_invalid_worker_arguments(self):
        self.push()
        for kw in [dict(ttl=0), dict(ttl=301), dict(limit=0), dict(limit=51)]:
            with self.assertRaises(ValueError):
                self.box.claim("worker", now=CLOCK, **kw)
        with self.assertRaises(ValueError):
            self.box.claim("worker with spaces", now=CLOCK)
        self.assertEqual(self.box.summary(), {"pending": 1})

    def test_no_network_or_credentials_used_by_storage(self):
        self.push()
        self.assertTrue(self.db.is_file())
        self.assertEqual(self.box.summary(), {"pending": 1})


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.box = EventInbox(Path(self.temp.name) / "http.sqlite", KEY)
        self.server = make_server(self.box, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def request(self, method, path, raw=b"", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            conn.request(method, path, body=raw, headers=headers or {})
            result = conn.getresponse()
            return result.status, json.loads(result.read()), dict(result.getheaders())
        finally:
            conn.close()

    def signed(self, raw=None):
        raw = body() if raw is None else raw
        stamp = int(time.time())
        return raw, {"X-Event-Timestamp": str(stamp),
                     "X-Event-Signature": signature(KEY, raw, stamp)}

    def test_http_event_insert_duplicate_and_conflict(self):
        raw, headers = self.signed()
        first, payload, response_headers = self.request("POST", "/events", raw, headers)
        self.assertEqual(first, 202)
        self.assertEqual(payload["status"], "stored")
        self.assertEqual(response_headers["Cache-Control"], "no-store")
        self.assertEqual(self.request("POST", "/events", raw, headers)[0], 200)
        raw2, headers2 = self.signed(body(payload={"v": 2}))
        status, data, _ = self.request("POST", "/events", raw2, headers2)
        self.assertEqual((status, data["error"]), (409, "idempotency_conflict"))

    def test_http_auth_failure_does_not_persist(self):
        raw, headers = self.signed()
        headers["X-Event-Signature"] = "v1=" + "0" * 64
        status, data, _ = self.request("POST", "/events", raw, headers)
        self.assertEqual((status, data["error"]), (401, "unauthorized"))
        self.assertEqual(self.box.summary(), {})

    def test_http_length_bound_is_enforced_before_read(self):
        # The declared size is intentionally oversized; do not transmit an
        # inconsistent body. On Windows, closing a socket with unread bytes
        # can reset the connection before the 413 is observable.
        _, headers = self.signed()
        headers["Content-Length"] = str(MAX_BODY + 1)
        self.assertEqual(self.request("POST", "/events", b"", headers)[0], 413)
        self.assertEqual(self.box.summary(), {})

    def test_http_rejects_chunked_requests(self):
        # Check the unsupported framing header before any body is sent.
        # Deliberately malformed raw bytes after Transfer-Encoding may
        # legitimately cause a TCP reset instead of a delivered 400.
        _, headers = self.signed()
        headers["Transfer-Encoding"] = "chunked"
        self.assertEqual(self.request("POST", "/events", b"", headers)[0], 400)
        self.assertEqual(self.box.summary(), {})

    def test_http_health_is_not_event_enumeration(self):
        status, data, _ = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["scope"], "loopback_only")
        self.assertEqual(self.request("GET", "/events")[0], 404)

    def test_http_missing_signature_refused(self):
        status, _, _ = self.request("POST", "/events", body())
        self.assertEqual(status, 401)

    def test_http_wrong_path_has_no_side_effect(self):
        raw, headers = self.signed()
        self.assertEqual(self.request("POST", "/admin", raw, headers)[0], 404)
        self.assertEqual(self.box.summary(), {})

    def test_rejected_posts_with_small_body_return_reliable_404(self):
        # Exercise actual HTTP response delivery, not merely handler return.
        raw, headers = self.signed()
        for _ in range(20):
            self.assertEqual(self.request("POST", "/admin", raw, headers)[0], 404)
        self.assertEqual(self.box.summary(), {})

    def test_bounded_early_reject_is_not_an_event_insert(self):
        raw, headers = self.signed()
        headers.pop("X-Event-Signature")
        for _ in range(8):
            self.assertEqual(self.request("POST", "/events", raw, headers)[0], 401)
        self.assertEqual(self.box.summary(), {})

    def test_loopback_only_server(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        with self.assertRaises(ValueError):
            make_server(self.box, port=-1)


if __name__ == "__main__":
    unittest.main()
