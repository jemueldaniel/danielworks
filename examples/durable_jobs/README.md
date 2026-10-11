# Durable job recovery

## Problem and implementation

A worker can disappear after claiming a job. Retrying forever is unsafe, but accepting a late result from an expired worker is unsafe too. This example implements a small durable queue with submission replay, request conflicts, bounded attempts, expiry recovery, generation fencing, cancellation, and atomic completion.

The implementation is newly written Python and SQL with AI assistance. The public code and tests—not private project descriptions—are the evidence being offered here.

## Architecture

`submit → pending → claim → running → complete → done`

`running → retry → pending/failed`, and `pending/running → cancel → cancelled`.

A SQLite file stores one row per `(tenant, key)`. `BEGIN IMMEDIATE` encloses selection and mutation so two connections cannot both claim the same pending row. Every successful claim increments its generation and attempt count. Completion and retry require the current generation, a running state, and a still-valid lease. No function runs the job's external action; the caller handles useful work separately.

## Run and test

Prerequisite: Python 3.11+ with its standard-library SQLite support. No packages, server, account or installation command is needed. Run from the repository root:

```sh
python examples/durable_jobs/demo.py
python -B -m unittest discover -s examples/durable_jobs -p 'test_*.py' -v
```

The demo submits `{"items": [2, 4, 6]}`, closes the first connection to simulate a lost worker, reopens the real database, and advances a synthetic clock past the lease. Its output is:

```json
{"attempts": 2, "result": {"count": 3}, "stale_worker_rejected": true, "status": "done"}
```

Both demo and tests create temporary databases and remove them after closing their connections. Do not point this schema-creating example at an existing application database.

## Decisions and tradeoffs

The idempotency identity includes tenant, key, canonical JSON payload and retry policy. A replay returns the existing state—even for completed or cancelled jobs. A different payload under the same key raises `Conflict`; starting new work requires a new key. Object key order is normalized, but distinct JSON encodings such as `1` and `1.0` are intentionally not treated as interchangeable.

A lease is valid on the half-open interval `[leased_at, lease_until)`. Ticks are caller-supplied nonnegative integers. Workers must share a trusted time basis; this is not clock synchronization. An expired final attempt becomes failed when that tenant is next polled. There is no background sweeper.

Payloads and results are plain JSON with a 4,096-byte, 512-value and 12-level nesting budget. Identifiers are bounded lowercase ASCII. SQL values are parameter-bound. A 100-millisecond database lock wait is surfaced as a SQLite exception; the library does not hide contention behind unbounded retries. Use one connection per thread and close it when finished.

## What the tests establish

Tests use real temporary SQLite files, two concurrent connections, a deliberately held write lock, a failure-injection SQL trigger, and close/reopen recovery. They check stale and expired leases, terminal replay, cancellation, tenant partitioning, retry exhaustion, rollback, caller-data aliasing and invalid inputs. The clock and worker disappearance are simulated; no process is killed, no machine is rebooted, and no power-loss durability claim is made.

## Known limits

Tenant IDs are a **trusted partition selector, not authentication or authorization**. Workers with database access are trusted; the lease object is not a cryptographic capability. There is no encryption, retention policy, schema migration system, fairness guarantee, database replication or multi-host qualification. Selection currently scans a small table; no throughput claim is made.

The generation check only fences this database result. It cannot undo a payment, email, model call or other outside effect. Exactly-once external side effects would require an independently enforced idempotency/reconciliation contract at that effect's owner. Cancellation stops future database completion; it does not forcibly stop a worker process.
