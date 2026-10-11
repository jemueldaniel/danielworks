# Typed API + SDK core

A dependency-free in-process demonstration of API design concerns that also apply to HTTP services: exact payload validation, tenant-scoped idempotency, bounded cursor pagination, and a client SDK that traverses pages safely.

Run: `python -m unittest -v test_service.py` from this directory.

Tradeoffs: transport/auth are deliberately omitted so the example isolates API semantics. No production database or network is implied.
