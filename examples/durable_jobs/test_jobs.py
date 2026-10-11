"""Real temporary SQLite databases; clocks and worker failures are simulated."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from jobs import Conflict, JobQueue, LeaseLost


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "jobs.sqlite"
        self.queue = JobQueue(self.path)

    def tearDown(self):
        self.queue.close()
        self.directory.cleanup()

    def submit(self, key="example", **kwargs):
        return self.queue.submit("team-a", key, {"task": "count", "items": [1, 2]}, **kwargs)

    def test_submission_replays_but_payload_conflict_does_not_overwrite(self):
        self.assertEqual(self.submit(), "pending")
        self.assertEqual(self.submit(), "pending")
        with self.assertRaises(Conflict):
            self.queue.submit("team-a", "example", {"task": "different"})
        self.assertEqual(self.queue.inspect("team-a", "example")["payload"]["task"], "count")

    def test_retry_policy_is_part_of_submission_identity(self):
        self.submit(max_attempts=2)
        with self.assertRaises(Conflict):
            self.submit(max_attempts=3)

    def test_completion_replay_is_observable_without_reexecuting(self):
        self.submit()
        lease = self.queue.claim("team-a", now=0, lease_ticks=10)
        self.queue.complete(lease, {"count": 2}, now=1)
        self.assertEqual(self.submit(), "done")
        self.assertIsNone(self.queue.claim("team-a", now=2))
        self.assertEqual(self.queue.inspect("team-a", "example")["result"], {"count": 2})
        with self.assertRaises(LeaseLost):
            self.queue.complete(lease, {"count": 999}, now=2)

    def test_reopen_recovers_expired_lease_and_fences_old_worker(self):
        self.submit()
        old = self.queue.claim("team-a", now=0, lease_ticks=5)
        self.queue.close()
        self.queue = JobQueue(self.path)
        new = self.queue.claim("team-a", now=5, lease_ticks=5)
        self.assertGreater(new.generation, old.generation)
        self.assertEqual(new.attempt, 2)
        with self.assertRaises(LeaseLost):
            self.queue.complete(old, {"stale": True}, now=6)
        self.queue.complete(new, {"recovered": True}, now=6)
        self.assertEqual(self.queue.inspect("team-a", "example")["result"], {"recovered": True})

    def test_expiry_boundary_rejects_completion_before_any_replacement(self):
        self.submit()
        lease = self.queue.claim("team-a", now=0, lease_ticks=5)
        with self.assertRaises(LeaseLost):
            self.queue.complete(lease, {}, now=5)

    def test_cancel_fences_running_worker_and_never_resurrects(self):
        self.submit()
        lease = self.queue.claim("team-a", now=0)
        self.assertTrue(self.queue.cancel("team-a", "example"))
        self.assertFalse(self.queue.cancel("team-a", "example"))
        with self.assertRaises(LeaseLost):
            self.queue.retry(lease, now=1)
        with self.assertRaises(LeaseLost):
            self.queue.complete(lease, {}, now=1)
        self.assertIsNone(self.queue.claim("team-a", now=100))
        self.assertEqual(self.submit(), "cancelled")

    def test_completed_job_cannot_be_cancelled(self):
        self.submit()
        lease = self.queue.claim("team-a", now=0)
        self.queue.complete(lease, {}, now=1)
        self.assertFalse(self.queue.cancel("team-a", "example"))

    def test_tenant_queues_and_same_keys_are_isolated(self):
        self.submit()
        self.queue.submit("team-b", "example", {"task": "other"})
        self.queue.cancel("team-b", "example")
        self.assertEqual(self.queue.inspect("team-a", "example")["state"], "pending")
        self.assertIsNone(self.queue.claim("team-b", now=0))
        self.assertEqual(self.queue.claim("team-a", now=0).tenant, "team-a")
        self.assertIsNone(self.queue.inspect("team-c", "example"))

    def test_retry_waits_until_ready_time_then_exhausts_budget(self):
        self.submit(max_attempts=2)
        first = self.queue.claim("team-a", now=0, lease_ticks=20)
        self.assertEqual(self.queue.retry(first, now=1, delay_ticks=4), "pending")
        self.assertIsNone(self.queue.claim("team-a", now=4))
        second = self.queue.claim("team-a", now=5)
        self.assertEqual(self.queue.retry(second, now=6), "failed")
        self.assertIsNone(self.queue.claim("team-a", now=100))
        self.assertEqual(self.queue.inspect("team-a", "example")["attempts"], 2)

    def test_expired_final_attempt_becomes_failed(self):
        self.submit(max_attempts=1)
        self.queue.claim("team-a", now=0, lease_ticks=2)
        self.assertIsNone(self.queue.claim("team-a", now=2))
        self.assertEqual(self.queue.inspect("team-a", "example")["state"], "failed")

    def test_concurrent_connections_cannot_claim_same_job(self):
        self.submit()
        barrier = threading.Barrier(2)

        def claim():
            with JobQueue(self.path) as worker:
                barrier.wait(timeout=2)
                return worker.claim("team-a", now=0, lease_ticks=10)

        with ThreadPoolExecutor(max_workers=2) as pool:
            leases = list(pool.map(lambda _: claim(), range(2)))
        self.assertEqual(sum(lease is not None for lease in leases), 1)
        self.assertEqual(self.queue.inspect("team-a", "example")["attempts"], 1)

    def test_sql_failure_rolls_back_and_connection_remains_usable(self):
        self.submit()
        lease = self.queue.claim("team-a", now=0)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("""CREATE TRIGGER fail_completion BEFORE UPDATE ON jobs
                WHEN NEW.state = 'done' BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.queue.complete(lease, {"count": 2}, now=1)
        self.assertEqual(self.queue.inspect("team-a", "example")["state"], "running")
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("DROP TRIGGER fail_completion")
        self.queue.complete(lease, {"count": 2}, now=1)

    def test_database_lock_is_reported_without_losing_pending_job(self):
        self.submit()
        blocker = sqlite3.connect(self.path, isolation_level=None)
        try:
            blocker.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                self.queue.claim("team-a", now=0)
        finally:
            blocker.execute("ROLLBACK")
            blocker.close()
        self.assertEqual(self.queue.inspect("team-a", "example")["attempts"], 0)
        self.assertIsNotNone(self.queue.claim("team-a", now=0))

    def test_payload_snapshots_do_not_alias_callers(self):
        payload = {"items": [1]}
        self.queue.submit("team-a", "example", payload)
        payload["items"].append(2)
        view = self.queue.inspect("team-a", "example")
        view["payload"]["items"].append(3)
        self.assertEqual(self.queue.inspect("team-a", "example")["payload"], {"items": [1]})

    def test_invalid_json_and_large_payload_are_rejected_before_insertion(self):
        cyclic = []; cyclic.append(cyclic)
        for payload in [float("nan"), {1: "bad key"}, {"x": object()}, cyclic, "x" * 5000]:
            with self.subTest(payload_type=type(payload).__name__), self.assertRaises(ValueError):
                self.queue.submit("team-a", "example", payload)
        self.assertIsNone(self.queue.inspect("team-a", "example"))

    def test_invalid_identifiers_times_and_attempts_are_rejected(self):
        for name in ["", "team'; DROP TABLE jobs;--", "x" * 65, 1, None]:
            with self.subTest(name_type=type(name).__name__), self.assertRaises(ValueError):
                self.queue.submit(name, "example", {})
        for now in [-1, True, 0.5, float("inf"), 2**60]:
            with self.subTest(now=repr(now)), self.assertRaises(ValueError):
                self.queue.claim("team-a", now=now)
        for attempts in [0, 11, True, 1.5]:
            with self.subTest(attempts=attempts), self.assertRaises(ValueError):
                self.submit(max_attempts=attempts)

    def test_lease_duration_validation_does_not_claim_job(self):
        self.submit()
        for ticks in [0, -1, True, 1_000_001]:
            with self.subTest(ticks=ticks), self.assertRaises(ValueError):
                self.queue.claim("team-a", now=0, lease_ticks=ticks)
        self.assertEqual(self.queue.inspect("team-a", "example")["attempts"], 0)


if __name__ == "__main__":
    unittest.main()
