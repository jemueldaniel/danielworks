# Design, decisions and limits

## One problem, two vertical interfaces

The application compares a lexical baseline with an actual SQLite FTS5/BM25 index, queues an evaluation, persists per-query progress and explains failures. The corpus is intentionally small and synthetic. The engineering evidence is the coherent execution and recovery path, not corpus size or invented quality claims.

The browser and MCP tools share the same Python backend and database. The Node gateway serves static React assets, enforces request/session bounds and translates same-origin API routes into real loopback requests. The public MCP SDK handles wire framing and protocol lifecycle; application code owns tool schemas, the catalog and permission profiles.

## Preserved components, explicit coupling

`examples/durable_jobs/jobs.py` continues to own submissions, leases, generations, attempts, cancellation and completion. `examples/ranking_eval/evaluation.py` owns the ranking grader. `examples/read_client/client.mts` supplies bounded, validated read retries. `examples/retrieval_lab/retrieval.py` remains the lexical comparison baseline. None of their source or tests were changed.

The checkpoint adapter deliberately queries the queue's table schema. A single `INSERT … SELECT` writes progress only when tenant, key, state, lease window and generation still match. It never updates queue-owned lease/state columns. This avoids copying the queue implementation but creates **schema coupling**, which the integration tests pin. A future queue schema change needs a versioned adapter, not assumptions.

## Persistence and recovery

Each operation owns and closes its SQLite connection. Foreign keys are enabled for checkpoint writes. The workbench has a version-1 migration and refuses unknown `user_version` or dataset identity drift. This is a small versioned schema, not a general migration framework or PostgreSQL example. Always use an explicit new example database: the preserved queue initializes its table before the workbench's version gate.

A run binds engine/cutoff to a canonical fixture digest. A checkpoint stores query identity, ranking, request digest, input digest, checksum and generation. On reclaim, the worker validates these fields before reusing progress. Corrupt progress fails closed. Checksums detect accidental corruption; they are not signatures and do not defend against an attacker who can rewrite the database and recompute hashes.

An actual process test exits after its first committed checkpoint, waits for real lease expiry, starts a new worker and verifies resumed work without replaying a terminal result. This is process-crash evidence, not power-loss, filesystem-corruption, network-filesystem or disaster-recovery qualification.

The default lease is 30 seconds and the original queue allows three attempts. A partial `max_cases` invocation leaves a running lease; it is reclaimed only after expiry. Repeated one-case slices can exhaust the three-attempt budget before finishing five cases. Use the default five-case batch for normal operation. This is a bounded retrying worker, not a multi-node distributed scheduler or a streaming batch service.

Cancellation advances the queue's fence. A stale worker cannot checkpoint or mark the cancelled generation complete. Abort of an HTTP/MCP request means the caller stopped waiting; it does **not** establish rollback or durable cancellation. `run_cancel` / `Cancel run` is the explicit durable operation. External side effects and exactly-once effects are out of scope.

## Typed boundaries and uncertain outcomes

Zod validates caller input and server output at runtime; TypeScript adds compile-time checks but does not replace validation. Successful write responses must also match the submitted key, engine and cutoff. A valid object for a different operation is classified as an unknown outcome, not confirmation.

The read client may retry safe GETs within a deadline. Mutation clients make one POST, never automatically replay it, and distinguish `not_sent`, `rejected` and `unknown`. Backend failure, response loss or invalid confirmation can be unknown even after a durable commit.

The UI stores the exact request identity before submission. It restores that request after reload, blocks new submissions while unresolved, and requires inspection. If found, it clears the draft without another POST. If absent, it offers an explicit same-key retry. A malformed draft blocks submission until explicitly discarded. Cross-tab coordination and multi-device draft recovery are not implemented.

## Protocol and resource scope

The installed official SDK is **1.32.1** and the qualified protocol version is **2025-11-25**. This is Streamable HTTP with JSON responses, not a handwritten imitation. Standalone GET/SSE is intentionally rejected; stream resumption, OAuth, remote identity providers, MCP resources/prompts, elicitation and a general conformance suite are not implemented or claimed. WebMCP is a separate, unqualified surface.

The gateway permits at most 16 initialized/pending sessions, 24 connections, 8 KiB requests and 64 KiB decoded backend responses. It checks literal loopback Host/Origin and profile/session binding. Idle sessions expire after two minutes; DELETE capacity recovery was executed in tests, but the full wall-clock TTL path was not separately waited out. The Python server admits at most 12 request threads. SDK deadlines and five-query batches bound individual operations.

The durable database can grow with explicit submissions. There is no disk quota, retention daemon or adversarial load qualification. These finite tests do not prove high-scale resource safety.

## UI and packaging choices

React was chosen because source-backed component behavior could be represented without inventing a Next.js deployment or SSR boundary. Native controls, labels, focus-visible styles, a native modal, live statuses and a responsive grid keep keyboard/error paths inspectable. Edge tests exercise actual interaction at 1280×800 and 390×844. Narrow viewport emulation is not a physical mobile-device test. No screen-reader, Safari, Firefox, touch-device or formal WCAG certification is claimed.

Dependencies are exact-pinned in the lockfile. Install scripts are disabled. An explicit local package resolver keeps esbuild from taking dependencies from an unrelated ancestor Yarn manifest; it does not edit parent files. Two narrow transport assertions bridge the SDK v1 optional-property declaration mismatch under strict TypeScript. Runtime wire tests still use the actual, unmodified SDK transports.

Structured diagnostics expose request IDs, status and elapsed milliseconds, not input bodies, database paths or credentials. Elapsed times are diagnostics, not benchmark claims. There are no production credentials, analytics collectors, CI workflows, auto-deploy hooks or live funds in this candidate.
