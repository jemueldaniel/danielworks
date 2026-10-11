"""Original bounded dependency-DAG planning and proof-bound local work claims.

No private source, arbitrary command execution, model calls or cloud services.
This is NOT a distributed scheduler, sandbox, cryptographic signature or IAM.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from threading import Lock
import time
import uuid
from typing import Callable

_ID = re.compile(r"[a-z][a-z0-9_-]{1,39}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
ZERO = "0" * 64
MAX_TASKS = 64
MAX_TOKENS = 16


class GraphError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def fail(code: str) -> None:
    raise GraphError(code)


def _name(value: object) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        fail("invalid_identifier")
    return value


def _digest(value: object) -> str:
    if type(value) is not str or not _DIGEST.fullmatch(value):
        fail("invalid_digest")
    return value


@dataclass(frozen=True)
class Task:
    name: str
    deps: tuple[str, ...]
    input_sha256: str
    tokens: int


def task(name: str, deps: tuple[str, ...] = (),
         input_sha256: str = ZERO, tokens: int = 1) -> Task:
    _name(name)
    _digest(input_sha256)
    if type(deps) is not tuple or len(deps) > MAX_TASKS:
        fail("invalid_dependencies")
    for dep in deps:
        _name(dep)
    if len(set(deps)) != len(deps) or name in deps:
        fail("invalid_dependencies")
    if type(tokens) is not int or not 1 <= tokens <= MAX_TOKENS:
        fail("invalid_tokens")
    return Task(name, tuple(deps), input_sha256, tokens)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


class Graph:
    """Immutable validated plans and stable source-dependent task fingerprints."""

    def __init__(self, tasks: list[Task]) -> None:
        if type(tasks) is not list or not 1 <= len(tasks) <= MAX_TASKS:
            fail("invalid_task_collection")
        items: dict[str, Task] = {}
        for t in tasks:
            if type(t) is not Task or task(t.name, t.deps, t.input_sha256, t.tokens) != t:
                fail("invalid_task")
            if t.name in items:
                fail("duplicate_task")
            items[t.name] = t
        for t in items.values():
            if any(dep not in items for dep in t.deps):
                fail("unknown_dependency")
        self.tasks = dict(sorted(items.items()))
        outgoing: dict[str, list[str]] = {name: [] for name in self.tasks}
        indegree = {name: len(t.deps) for name, t in self.tasks.items()}
        for t in self.tasks.values():
            for dep in t.deps:
                outgoing[dep].append(t.name)
        self.outgoing = {k: tuple(sorted(v)) for k, v in outgoing.items()}

        order: list[str] = []
        layers: list[tuple[str, ...]] = []
        pending = dict(indegree)
        while len(order) < len(items):
            ready = tuple(sorted(k for k, v in pending.items() if v == 0))
            if not ready:
                fail("cycle")
            layers.append(ready)
            for name in ready:
                del pending[name]
                order.append(name)
                for successor in outgoing[name]:
                    pending[successor] -= 1
        self.order = tuple(order)
        self.layers = tuple(layers)

        fingerprints = {}
        for name in self.order:
            t = self.tasks[name]
            canonical = [name, t.input_sha256, t.tokens,
                         [[dep, fingerprints[dep]] for dep in sorted(t.deps)]]
            fingerprints[name] = hashlib.sha256(_canonical(canonical)).hexdigest()
        self.fingerprints = dict(sorted(fingerprints.items()))
        self.plan_sha256 = hashlib.sha256(
            _canonical(self.fingerprints)).hexdigest()

        longest = {}
        for name in reversed(self.order):
            children = self.outgoing[name]
            longest[name] = self.tasks[name].tokens + (
                max(longest[c] for c in children) if children else 0)
        self.downstream_cost = longest

    def affected(self, changed: tuple[str, ...]) -> tuple[str, ...]:
        if type(changed) is not tuple or len(set(changed)) != len(changed):
            fail("invalid_changed_tasks")
        for name in changed:
            _name(name)
            if name not in self.tasks:
                fail("unknown_task")
        impacted = set(changed)
        work = list(changed)
        while work:
            for successor in self.outgoing[work.pop()]:
                if successor not in impacted:
                    impacted.add(successor)
                    work.append(successor)
        return tuple(name for name in self.order if name in impacted)

    def changed_since(self, previous: dict[str, str]) -> tuple[str, ...]:
        if type(previous) is not dict:
            fail("invalid_previous_plan")
        if any(type(key) is not str or type(value) is not str
               for key, value in previous.items()):
            fail("invalid_previous_plan")
        return tuple(name for name in self.order
                     if self.fingerprints[name] != previous.get(name))

    def describe(self) -> dict:
        return {
            "plan_sha256": self.plan_sha256,
            "layers": [list(layer) for layer in self.layers],
            "order": list(self.order),
            "critical_tokens": max(self.downstream_cost.values()),
            "max_tasks": MAX_TASKS,
            "scope": "local original public DAG planning; no external execution",
        }


class Coordinator:
    """Thread-safe in-memory dependency gate with expiring, fenced claims.

    Workers run their own trusted code OUTSIDE this class. A claim is an
    advisory test lease, not an authentication token or exactly-once effect.
    """

    def __init__(self, graph: Graph, capacity: int = 4,
                 lease_seconds: float = 30.0, max_attempts: int = 2,
                 clock: Callable[[], float] = time.monotonic) -> None:
        if type(graph) is not Graph:
            fail("invalid_graph")
        if type(capacity) is not int or not 1 <= capacity <= MAX_TOKENS:
            fail("invalid_capacity")
        if any(t.tokens > capacity for t in graph.tasks.values()):
            fail("unschedulable_task")
        if type(lease_seconds) not in (int, float) or not 0.01 <= lease_seconds <= 3600:
            fail("invalid_lease")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 10:
            fail("invalid_attempts")
        if not callable(clock):
            fail("invalid_clock")
        self.graph = graph
        self.capacity = capacity
        self.lease_seconds = float(lease_seconds)
        self.max_attempts = max_attempts
        self.clock = clock
        self.lock = Lock()
        self.states = {name: "PENDING" for name in graph.order}
        self.attempts = {name: 0 for name in graph.order}
        self.active: dict[str, dict] = {}
        self.output_sha256: dict[str, str] = {}

    def _block_dependents(self) -> None:
        for name in self.graph.order:
            if self.states[name] != "PENDING":
                continue
            if any(self.states[dep] in ("FAILED", "BLOCKED")
                   for dep in self.graph.tasks[name].deps):
                self.states[name] = "BLOCKED"

    def _expire(self, now: float) -> None:
        for name, current in list(self.active.items()):
            if now >= current["deadline"]:
                del self.active[name]
                self.states[name] = ("FAILED" if self.attempts[name] >= self.max_attempts
                                     else "PENDING")
        self._block_dependents()

    def claim(self, worker: str) -> dict | None:
        _name(worker)
        with self.lock:
            now = self.clock()
            self._expire(now)
            used = sum(self.graph.tasks[name].tokens for name in self.active)
            remaining = self.capacity - used
            ready = (name for name in self.graph.order
                     if self.states[name] == "PENDING"
                     and self.graph.tasks[name].tokens <= remaining
                     and all(self.states[dep] == "DONE"
                             for dep in self.graph.tasks[name].deps))
            priority = sorted(ready, key=lambda name:
                              (-self.graph.downstream_cost[name], name))
            if not priority:
                return None
            name = priority[0]
            self.attempts[name] += 1
            token = uuid.uuid4().hex
            deadline = now + self.lease_seconds
            self.states[name] = "ACTIVE"
            self.active[name] = {
                "token": token, "worker": worker, "deadline": deadline,
            }
            return {
                "task": name, "worker": worker, "lease": token,
                "attempt": self.attempts[name], "deadline": deadline,
                "tokens": self.graph.tasks[name].tokens,
                "input_fingerprint": self.graph.fingerprints[name],
            }

    def _require_current(self, name: str, worker: str, lease: str) -> None:
        _name(name)
        _name(worker)
        if type(lease) is not str or not re.fullmatch(r"[0-9a-f]{32}", lease):
            fail("lease_not_current")
        current = self.active.get(name)
        if (not current or self.states[name] != "ACTIVE" or
                current["token"] != lease or current["worker"] != worker):
            fail("lease_not_current")

    def complete(self, name: str, worker: str, lease: str,
                 output_sha256: str) -> str:
        _digest(output_sha256)
        with self.lock:
            self._expire(self.clock())
            self._require_current(name, worker, lease)
            del self.active[name]
            self.output_sha256[name] = output_sha256
            self.states[name] = "DONE"
            return "DONE"

    def reject(self, name: str, worker: str, lease: str) -> str:
        with self.lock:
            self._expire(self.clock())
            self._require_current(name, worker, lease)
            del self.active[name]
            self.states[name] = ("FAILED" if self.attempts[name] >= self.max_attempts
                                 else "PENDING")
            self._block_dependents()
            return self.states[name]

    def snapshot(self) -> dict:
        with self.lock:
            self._expire(self.clock())
            return {
                "plan_sha256": self.graph.plan_sha256,
                "states": dict(self.states),
                "attempts": dict(self.attempts),
                "active_tokens_used": sum(self.graph.tasks[n].tokens for n in self.active),
                "capacity": self.capacity,
                "all_terminal": all(s in ("DONE", "FAILED", "BLOCKED")
                                    for s in self.states.values()),
            }

    def receipt(self) -> dict:
        with self.lock:
            self._expire(self.clock())
            if any(s not in ("DONE", "FAILED", "BLOCKED") for s in self.states.values()):
                fail("not_terminal")
            results = [
                [name, self.graph.fingerprints[name],
                 self.states[name], self.attempts[name],
                 self.output_sha256.get(name)]
                for name in self.graph.order
            ]
            payload = {
                "schema": 1, "plan_sha256": self.graph.plan_sha256,
                "results": results,
                "status": "PASS" if all(s == "DONE" for s in self.states.values())
                          else "INCOMPLETE",
                "qualification": "in-memory local claims only; no independent execution attestation",
            }
            payload["receipt_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
            return payload
