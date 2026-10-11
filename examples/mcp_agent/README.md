# MCP-style in-process agent recovery exercise

This is the preserved JavaScript registry/server/runner exercise, not the real MCP transport in the workbench. It supports explicit schema callbacks, per-tool permission checks, cooperative cancellation and **RAM-only** checkpoints in a shared `Map`. A `Map` is not durable storage.

From the repository root:

```sh
node --test --test-concurrency=1 examples/mcp_agent/test_runtime.mjs
```

## Recovery contract

Checkpoint **version 1** binds the run ID, ordered JSON steps and permission set to a request hash. The runner validates the checkpoint schema, progress, result count and checksum before resuming. Changed requests fail with `run_input_conflict`; malformed or modified checkpoints fail with `invalid_checkpoint`. Legacy unbound checkpoints are rejected and preserved, not silently migrated or replayed. An operator must reconcile any prior effects before deciding to discard an old checkpoint or use a new run ID.

Arguments are snapshotted before execution, and stored/returned results do not share mutable objects. JSON object-key order and permission insertion order do not alter identity. The live permission set is checked between steps: removing or changing capabilities stops subsequent calls. An already-running tool still requires cooperative cancellation through its signal.

Concurrent calls for the same run ID and the **same Map object** fail with `run_in_progress`, including calls from separate `AgentRunner` instances. Different run IDs remain independent. This guard is process-local; it does not coordinate workers, processes, another copy of a Map, or an external store. The supported checkpoint store is a `Map`, not an asynchronous database adapter.

Each invocation captures its starting server and Map: **per-run server/store binding** prevents reassignment of the runner's public fields from redirecting an already suspended run. Later invocations may use reconfigured fields. This is not authentication or a freeze of the selected objects: a caller able to mutate server implementations or forge consistent Map contents remains outside the trust boundary. Live permission revocation still applies between steps.

The runner accepts at most 64 steps, 64 explicit permissions, and 1–64-character ASCII run/tool/permission identifiers. JSON snapshots reject cycles, non-finite numbers, undefined/functions, accessors, sparse arrays and non-plain objects; each snapshot is bounded to 2,048 visited values, depth 16 and 65,536 UTF-8 encoded bytes. Tool results must fit the same JSON boundary before their completion can be recorded.

## Effects and integrity limits

The guarantee is **no replay of validated, recorded completions**, not exactly-once external effects. A tool can act and then fail, lose its response, exceed the result limit, or be interrupted before checkpoint recording. An explicit retry may repeat that effect. Real effectful integrations need their own idempotency/reconciliation design; this example does not supply one.

The SHA-256 checksum detects inconsistent checkpoint bytes; it is not a signature, authentication, a secret, or protection from a party that can replace both a checkpoint and its digest. Permission strings are supplied by the caller and are not an identity provider. Keeping checkpoints in separate stores is the caller's responsibility for separate trust domains.

The current 27-case Linux run preserves all 24 earlier definitions and adds three cases. Two suspended field-reassignment regressions failed before the per-run binding correction; the partial-checkpoint JSON/cancellation case adds coverage of existing behaviour. The full progression is recorded in [current verification](../../docs/CURRENT_VERIFICATION.md). Tests use the actual in-process implementation and synthetic tools. They do not qualify HTTP, browser-native WebMCP, process restart persistence, a real external side effect, Windows, or the dependency-locked workbench build. Whole-package independent review remains incomplete.
