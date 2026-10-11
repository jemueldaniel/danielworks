"""Real graph topology, content fingerprints, concurrency and lease fencing."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import threading
import time
import unittest

from graph import Task, Graph, GraphError, Coordinator, task, ZERO

ONE = "1" * 64
TWO = "2" * 64
THREE = "3" * 64


def pipeline():
    return Graph([task("stage-a"),
                  task("stage-b", ("stage-a",), tokens=2),
                  task("stage-c", ("stage-a",)),
                  task("stage-d", ("stage-b", "stage-c"))])


class Clock:
    def __init__(self):
        self.now = 100.0
    def __call__(self):
        return self.now
    def advance(self, seconds):
        self.now += seconds


class GraphTests(unittest.TestCase):
    def test_topological_layers(self):
        self.assertEqual(pipeline().layers, (("stage-a",), ("stage-b", "stage-c"), ("stage-d",)))
    def test_topological_order(self):
        self.assertEqual(pipeline().order, ("stage-a", "stage-b", "stage-c", "stage-d"))
    def test_critical_path(self):
        self.assertEqual(pipeline().describe()["critical_tokens"], 4)
    def test_fingerprints_stable_across_input_permutation(self):
        p = pipeline()
        q = Graph(list(reversed(list(p.tasks.values()))))
        self.assertEqual(p.plan_sha256, q.plan_sha256)
    def test_input_change_invalidates_dependents(self):
        p = pipeline()
        q = Graph([task("stage-a", input_sha256=ONE),
                   task("stage-b", ("stage-a",), tokens=2),
                   task("stage-c", ("stage-a",)),
                   task("stage-d", ("stage-b", "stage-c"))])
        self.assertEqual(q.changed_since(p.fingerprints), p.order)
    def test_unrelated_fingerprint_stays_constant(self):
        p = pipeline()
        q = Graph([task("stage-a"),
                   task("stage-b", ("stage-a",), input_sha256=TWO, tokens=2),
                   task("stage-c", ("stage-a",)),
                   task("stage-d", ("stage-b", "stage-c"))])
        self.assertEqual(q.changed_since(p.fingerprints), ("stage-b", "stage-d"))
    def test_affected_downstream_only(self):
        self.assertEqual(pipeline().affected(("stage-b",)), ("stage-b", "stage-d"))
    def test_affected_shared_descendants_once(self):
        self.assertEqual(pipeline().affected(("stage-b", "stage-c")),
                         ("stage-b", "stage-c", "stage-d"))
    def test_affected_empty(self):
        self.assertEqual(pipeline().affected(()), ())
    def test_unknown_impact_refused(self):
        with self.assertRaisesRegex(GraphError, "unknown_task"):
            pipeline().affected(("foreign",))
    def test_duplicate_changed_refused(self):
        with self.assertRaisesRegex(GraphError, "invalid_changed_tasks"):
            pipeline().affected(("stage-b", "stage-b"))
    def test_duplicate_task_refused(self):
        with self.assertRaisesRegex(GraphError, "duplicate_task"):
            Graph([task("alpha"), task("alpha")])
    def test_missing_dep_refused(self):
        with self.assertRaisesRegex(GraphError, "unknown_dependency"):
            Graph([task("alpha", ("not-created",))])
    def test_cycle_refused(self):
        with self.assertRaisesRegex(GraphError, "cycle"):
            Graph([task("alpha", ("bravo",)), task("bravo", ("alpha",))])
    def test_self_dep_refused(self):
        with self.assertRaisesRegex(GraphError, "invalid_dependencies"):
            task("alpha", ("alpha",))
    def test_duplicate_dep_refused(self):
        with self.assertRaisesRegex(GraphError, "invalid_dependencies"):
            task("alpha", ("bravo", "bravo"))
    def test_malformed_task_identifier_refused(self):
        with self.assertRaisesRegex(GraphError, "invalid_identifier"):
            task("../secret")
    def test_bad_input_digest_refused(self):
        for digest in ("xyz", "A"*64, "", None):
            with self.subTest(digest=digest), self.assertRaisesRegex(GraphError, "invalid_digest"):
                task("alpha", input_sha256=digest)
    def test_invalid_work_units_refused(self):
        for value in (0, 17, True, -1, 1.5):
            with self.subTest(value=value), self.assertRaisesRegex(GraphError, "invalid_tokens"):
                task("alpha", tokens=value)
    def test_bad_dependency_types_refused(self):
        with self.assertRaisesRegex(GraphError, "invalid_dependencies"):
            task("alpha", ["bravo"])
        with self.assertRaisesRegex(GraphError, "invalid_dependencies"):
            task("alpha", ("bravo",)*65)
    def test_empty_graph_refused(self):
        with self.assertRaisesRegex(GraphError, "invalid_task_collection"):
            Graph([])
    def test_oversized_graph_refused(self):
        with self.assertRaisesRegex(GraphError, "invalid_task_collection"):
            Graph([task("job-"+str(i)) for i in range(65)])
    def test_forged_dataclass_refused(self):
        with self.assertRaisesRegex(GraphError, "invalid_dependencies"):
            Graph([Task("alpha", [], ZERO, 1)])
    def test_many_independent_tasks_stable_order(self):
        g = Graph([task("job-"+str(i)) for i in reversed(range(24))])
        self.assertEqual(len(g.layers), 1)
        self.assertEqual(list(g.layers[0]), sorted(g.tasks))
    def test_deleted_fingerprint_detected(self):
        p = pipeline()
        prior = dict(p.fingerprints)
        del prior["stage-b"]
        self.assertEqual(p.changed_since(prior), ("stage-b",))
    def test_bad_previous_plan_refused(self):
        with self.assertRaisesRegex(GraphError, "invalid_previous_plan"):
            pipeline().changed_since({"stage-a": 42})


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.graph = pipeline()
        self.coord = Coordinator(self.graph, capacity=3, lease_seconds=4,
                                 max_attempts=2, clock=self.clock)
    def _done(self, lease):
        return self.coord.complete(lease["task"], lease["worker"], lease["lease"], ONE)
    def test_deps_not_ready_before_upstream(self):
        first = self.coord.claim("worker-one")
        self.assertEqual(first["task"], "stage-a")
        self.assertIsNone(self.coord.claim("worker-two"))
    def test_critical_path_priority(self):
        self._done(self.coord.claim("worker-one"))
        self.assertEqual(self.coord.claim("worker-two")["task"], "stage-b")
    def test_capacity_enforced(self):
        self._done(self.coord.claim("worker-one"))
        a = self.coord.claim("worker-one")
        b = self.coord.claim("worker-two")
        self.assertEqual({a["task"], b["task"]}, {"stage-b", "stage-c"})
        self.assertEqual(self.coord.snapshot()["active_tokens_used"], 3)
        self.assertIsNone(self.coord.claim("worker-three"))
    def test_dependents_ready_after_all_inputs(self):
        self._done(self.coord.claim("worker-one"))
        b = self.coord.claim("worker-one")
        c = self.coord.claim("worker-two")
        self._done(b)
        self.assertIsNone(self.coord.claim("worker-three"))
        self._done(c)
        self.assertEqual(self.coord.claim("worker-three")["task"], "stage-d")
    def test_full_run_receipt(self):
        while True:
            lease = self.coord.claim("worker-one")
            if lease is None:
                break
            self._done(lease)
        report = self.coord.receipt()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(len(report["results"]), 4)
        self.assertEqual(len(report["receipt_sha256"]), 64)
        self.assertEqual(report, self.coord.receipt())
    def test_nonterminal_receipt_disallowed(self):
        with self.assertRaisesRegex(GraphError, "not_terminal"):
            self.coord.receipt()
    def test_secret_lease_not_in_snapshot(self):
        lease = self.coord.claim("worker-one")
        self.assertNotIn(lease["lease"], json.dumps(self.coord.snapshot()))
    def test_bad_output_hash_fails_closed(self):
        lease = self.coord.claim("worker-one")
        with self.assertRaisesRegex(GraphError, "invalid_digest"):
            self.coord.complete("stage-a", "worker-one", lease["lease"], "not-a-hash")
        self.assertEqual(self.coord.snapshot()["states"]["stage-a"], "ACTIVE")
    def test_wrong_worker_fails_closed(self):
        lease = self.coord.claim("worker-one")
        with self.assertRaisesRegex(GraphError, "lease_not_current"):
            self.coord.complete("stage-a", "worker-two", lease["lease"], ONE)
    def test_wrong_lease_fails_closed(self):
        self.coord.claim("worker-one")
        with self.assertRaisesRegex(GraphError, "lease_not_current"):
            self.coord.complete("stage-a", "worker-one", "f"*32, ONE)
    def test_duplicate_completion_fails_closed(self):
        lease = self.coord.claim("worker-one")
        self._done(lease)
        with self.assertRaisesRegex(GraphError, "lease_not_current"):
            self._done(lease)
    def test_expiry_reissues_with_new_token(self):
        old = self.coord.claim("worker-one")
        self.clock.advance(5)
        new = self.coord.claim("worker-two")
        self.assertEqual(new["task"], old["task"])
        self.assertNotEqual(new["lease"], old["lease"])
        self.assertEqual(new["attempt"], 2)
    def test_stale_claim_cannot_commit(self):
        old = self.coord.claim("worker-one")
        self.clock.advance(5)
        self.coord.claim("worker-two")
        with self.assertRaisesRegex(GraphError, "lease_not_current"):
            self._done(old)
    def test_failure_blocks_dependents(self):
        first = self.coord.claim("worker-one")
        self.assertEqual(self.coord.reject("stage-a", "worker-one", first["lease"]), "PENDING")
        second = self.coord.claim("worker-one")
        self.assertEqual(self.coord.reject("stage-a", "worker-one", second["lease"]), "FAILED")
        states = self.coord.snapshot()["states"]
        self.assertEqual(states["stage-a"], "FAILED")
        self.assertEqual({states[x] for x in ("stage-b", "stage-c", "stage-d")}, {"BLOCKED"})
        self.assertEqual(self.coord.receipt()["status"], "INCOMPLETE")
    def test_expiry_at_max_attempts_blocks(self):
        self.coord.claim("worker-one")
        self.clock.advance(5)
        self.coord.claim("worker-one")
        self.clock.advance(5)
        self.assertIsNone(self.coord.claim("worker-one"))
        self.assertEqual(self.coord.snapshot()["states"]["stage-d"], "BLOCKED")
    def test_reject_wrong_worker_preserves_active(self):
        first = self.coord.claim("worker-one")
        with self.assertRaisesRegex(GraphError, "lease_not_current"):
            self.coord.reject("stage-a", "worker-two", first["lease"])
        self.assertEqual(self.coord.snapshot()["states"]["stage-a"], "ACTIVE")
    def test_capacity_too_small_rejected(self):
        with self.assertRaisesRegex(GraphError, "unschedulable_task"):
            Coordinator(self.graph, capacity=1)
    def test_bad_configuration_rejected(self):
        for kw in ({"capacity": True}, {"max_attempts": 0},
                   {"lease_seconds": 0}, {"lease_seconds": True}):
            with self.subTest(kw=kw), self.assertRaises(GraphError):
                Coordinator(self.graph, **kw)
    def test_invalid_worker_rejected(self):
        with self.assertRaisesRegex(GraphError, "invalid_identifier"):
            self.coord.claim("../worker")
    def test_parallel_workers_never_duplicate_results(self):
        g = Graph([task("job-"+str(i)) for i in range(25)])
        c = Coordinator(g, capacity=4)
        claimed = []
        lock = threading.Lock()
        def worker(i):
            for _ in range(250):
                claim = c.claim("worker-"+str(i))
                if claim is None:
                    if c.snapshot()["all_terminal"]:
                        return
                    time.sleep(0.001)
                    continue
                with lock:
                    claimed.append(claim["task"])
                c.complete(claim["task"], claim["worker"], claim["lease"], TWO)
            raise AssertionError("Worker exceeded bound")
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(worker, range(6)))
        self.assertEqual(len(claimed), 25)
        self.assertEqual(len(set(claimed)), 25)
        self.assertEqual(c.receipt()["status"], "PASS")
    def test_receipt_not_signature(self):
        for _ in range(4):
            self._done(self.coord.claim("worker-one"))
        report = self.coord.receipt()
        self.assertIn("in-memory", report["qualification"])
        self.assertNotIn("signature", report)
    def test_receipt_digest_binds_results(self):
        for _ in range(4):
            self._done(self.coord.claim("worker-one"))
        first = self.coord.receipt()
        altered = json.loads(json.dumps(first))
        altered["results"][0][4] = THREE
        self.assertNotEqual(
            sha256(json.dumps(first["results"], sort_keys=True).encode()).hexdigest(),
            sha256(json.dumps(altered["results"], sort_keys=True).encode()).hexdigest())

if __name__ == "__main__":
    unittest.main()
