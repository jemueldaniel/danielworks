# Signed event inbox + fenced local outbox

This is an **original public Python standard-library teaching reference** for a
transferable backend capability: accept bounded HMAC-signed events, persist
each event idempotently, and process them with expiring, generation-fenced
worker leases. It deliberately does not import private product source,
configuration, credentials, API contracts, brand names or business logic.

## Run real tests

From the repository root (Python 3.13 or compatible):

```sh
python -B -m unittest discover -s examples/event_outbox -v
python -B examples/event_outbox/demo.py
```

The acceptance suite checks a real loopback HTTP server, raw-byte signatures,
timestamp bounds, tampering, Unicode/JSON rejection, SQLite durability,
parallel insert races, concurrent lease exclusion, time-based recovery,
acknowledgment fencing, dead-letter handling and file release on Windows.
The same test module is included in the pinned one-command public exporter
under profile `event-outbox`.

## Design and semantics

1. A producer constructs a JSON object with exact keys `id`, `type`,
   `payload`. Its id uniquely identifies one immutable **byte-exact** event.
2. Producer sends HTTP `POST /events` with `X-Event-Timestamp` (seconds)
   and `X-Event-Signature` of the form `v1=<hex>`. The signed
   message is UTF-8 ASCII timestamp + a period + **raw JSON bytes**.
   A real deployment must distribute and rotate secrets securely.
3. The loopback adapter rejects duplicate/invalid headers, chunked requests,
   unsupported paths and bodies above 8192 bytes. The store validates a
   300-second skew window and HMAC *before* parsing or persisting.
4. SQLite uses short `BEGIN IMMEDIATE` transactions for idempotent
   inserts, leases, completions and release. A reused event id with different
   bytes returns HTTP 409; an identical retry returns HTTP 200 without a
   second delivery record.
5. Workers claim a bounded batch with a lease owner and monotonically
   increasing **generation**. An expired owner cannot acknowledge a newer
   generation. After the configured attempt budget, an unacknowledged event is
   moved to `dead`; callers must inspect/handle it explicitly.
6. A process can reopen the database and recover pending or expired work.
   The receipt exposes digest, state and generation, not a credential.

## Threat model and limits

The tests establish a **local, single-database at-least-once processing
reference**, not an internet-facing authenticated SaaS. HMAC authenticates
knowledge of a shared signing key; it does not authenticate humans, implement
encryption, encrypt payloads at rest, rotate keys, provide tenant separation,
or verify an upstream event source. Enforce TLS, authenticated administration,
rate limiting, key rotation, migration/backups, disk quotas, log hygiene,
monitoring and incident handling before adapting it for production.

Lease acknowledgments guard **local state transitions only**. A crashed worker
can perform an external side effect and lose its acknowledgment; that external
effect can repeat after re-lease. External consumers must implement their own
idempotency and reconciliation. Wall-clock leases require trustworthy time and
capacity tuning. This module has no cloud deployment, live provider calls,
distributed consensus, security certification or independent production audit.

For future employment, use this as a pattern to reimplement within the
employer's licensed repository and review process; never assume rights to move
any private project code or secrets.
