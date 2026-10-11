# Atomic double-entry journal (synthetic, offline)

An **original public** Python + SQLite exercise in bounded integer money-like arithmetic, tenant-partitioned accounts, atomic double-entry transfers, idempotency keys, concurrent writers, negative-balance prevention, deterministic per-tenant hash chains and independent journal/balance reconciliation.

**Not** a banking product, custody system, live crypto ledger, stablecoin implementation, database isolation policy, or audit certification. No real funds, wallet signing, credentials or private business logic are used. The API accepts a tenant label supplied by its caller; it **does not authenticate or authorize a caller**. The synthetic clearing account may run negative to illustrate conservation of postings, not real issuance or bank settlement. Stored SHA-256 chains are **unkeyed** and cannot protect against a malicious database administrator.

## Run

From the repository root, run:

    python -B -m unittest discover -s examples/atomic_ledger -v
    python -B examples/atomic_ledger/demo.py

## Invariants and failure modes

Every posted transfer writes one equal negative and positive posting under a single SQLite immediate transaction. The account balance cache updates in the same transaction. A repeated request ID with the same complete payload returns replay without reposting; reusing it for different amount/accounts/asset refuses with a conflict. The scope also enforces same-tenant accounts, same-asset transfers, integer-only bounded amounts and insufficient-funds rejection for ordinary accounts.

The audit replays postings, validates the serialized request digests and ordered per-tenant hash links, and checks each asset still totals zero. Negative tests introduce deliberate SQLite corruption and prove the audit detects it. The local transaction model is replay-safe for **database writes**; it cannot provide exactly-once external effects, protect against compromised database access, or replace independent production finance review.

For real-world integration, add server-side authentication, tenant/ownership authorization, account lifecycle and limits, real issuance/settlement providers, database permissions, durable backups, key management, migrations, monitoring, external reconciliation, and third-party review.
