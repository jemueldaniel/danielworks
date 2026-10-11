# Skills → inspectable evidence

Start with behavior and its tests. A library import, directory name, private source reference or historical plan is not public runnable proof.

| Skill / engineering judgment | Implementation | Executed evidence |
|---|---|---|
| TypeScript, API/SDK contracts, schema validation, pagination, idempotency | [HTTP SDK](../projects/evidence-workbench/src/api-client.ts), [schemas](../projects/evidence-workbench/src/schema.ts) | [Real SDK HTTP tests](../projects/evidence-workbench/tests/api.test.mjs), [identity mismatch regression](../projects/evidence-workbench/tests/review.test.mjs) |
| Node.js, MCP transport, sessions and tool permissions | [Gateway](../projects/evidence-workbench/src/server.ts), [tool catalog](../projects/evidence-workbench/src/mcp.ts), [MCP SDK wrapper](../projects/evidence-workbench/src/mcp-client.ts) | [Wire/client integration](../projects/evidence-workbench/tests/protocol.test.mjs), [session capacity/deletion](../projects/evidence-workbench/tests/review.test.mjs) |
| React, typed UI state, responsive/keyboard interfaces and recovery | [React application](../projects/evidence-workbench/web/App.tsx), [CSS](../projects/evidence-workbench/web/style.css) | [Actual browser suite](../projects/evidence-workbench/tests/browser.test.mjs): two viewports, keyboard, modal, loading, restart, offline and lost-response cases |
| Python, real SQL, versioned schema, concurrency and tenant partitioning | [Backend](../projects/evidence-workbench/backend/server.py), [store](../projects/evidence-workbench/backend/workbench.py) | [SQL/race tests](../projects/evidence-workbench/backend/test_workbench.py), [real HTTP tests](../projects/evidence-workbench/backend/test_http.py) |
| Durable jobs, scoped tools, finite execution, cancellation and replay recovery | [Preserved queue](../examples/durable_jobs/jobs.py), [checkpoint adapter](../projects/evidence-workbench/backend/workbench.py) | [Generation/cancellation tests](../projects/evidence-workbench/backend/test_workbench.py), [actual process-exit recovery](../projects/evidence-workbench/backend/test_process_recovery.py) |
| Retrieval, held-out evaluation, reproducible error analysis | [FTS5 path](../projects/evidence-workbench/backend/workbench.py), [versioned synthetic input](../projects/evidence-workbench/fixtures/corpus.v1.json), [preserved grader](../examples/ranking_eval/evaluation.py) | [Engine/grader tests](../projects/evidence-workbench/backend/test_workbench.py), [known failure and limits](../projects/evidence-workbench/README.md) |
| Rust, lexical/parser/IR/VM implementation and compiler regression diagnosis | [Bounded language](../projects/bounded-lang/src/lib.rs) | [Binding regression](../projects/bounded-lang/tests/bindings.rs), [compile budgets](../projects/bounded-lang/tests/compile_budget.rs), [runtime limits](../projects/bounded-lang/tests/limits.rs); 18 tests, formatting and clippy passed |
| Cross-version test-runner consistency and fail-closed summary parsing | [Original SDK test orchestrator](../tools/verify.py) | [Six version/format regressions](../tools/test_verify_runner.py); 60 original examples passed on Windows Node 24.15.0 and Linux Node 22.16.0 without claiming the locked workbench build |
| Git object integrity, path/mode protection, cross-platform source restoration | [Offline commit verifier](../tools/verify_git_commit.py), [filesystem verifier](../tools/verify_source.py) | [Nine local-Git edge cases](../tools/test_verify_git_commit.py), [28 source-verifier cases](../tools/test_verify_source.py); public baseline byte/readback identity in [current record](CURRENT_VERIFICATION.md) |
| Bounded HTTP early-rejection handling and response-loss semantics | [HTTP server](../projects/evidence-workbench/backend/server.py), [interface contract](../projects/evidence-workbench/docs/INTERFACES.md) | [28 backend tests](../projects/evidence-workbench/backend/test_http.py), including two added no-network rejection-accounting regressions and fresh Linux/Windows backend runs; historical intermittent Windows failure remains recorded |
| **Real, bounded CPU ML training** (synthetic input, no private dataset) | [Deterministic mini-batch logistic regression, standardization and checkpoint handling](../examples/synthetic_training/training.py) | [17 interruption, integrity, leakage, convergence and bounds tests](../examples/synthetic_training/test_training.py); [toy-only metrics](../examples/synthetic_training/README.md) |
| **Honest capability-to-evidence mapping** | [Public-only claim index](PUBLIC_CAPABILITIES.json), [structural claim verifier](../tools/verify_public_capabilities.py) | [13 fail-closed tests](../tools/test_verify_public_capabilities.py); *running this checker does not run the referenced tests* |
| Negative testing, bounded diagnostics, dependency/build reproducibility | [Build script](../projects/evidence-workbench/scripts/build.mjs), [lockfile](../package-lock.json), server diagnostic code | [Verification and failed-test record](TEST_EVIDENCE.md), [scope boundaries](../projects/evidence-workbench/docs/DESIGN.md) |

**Not established by this public candidate:** browser-native WebMCP; Next.js SSR/server actions; PostgreSQL/RLS or PostgreSQL concurrency; a production identity provider; an LLM agent; large-model training; compiled Solidity/EVM tests; a distributed cluster; original SVG/media authoring; production deployment or scale. See the [coverage matrix](COVERAGE_MATRIX.md). The coverage matrix is the single backlog and includes source-inspected but unqualified areas. Those gaps must not be filled with claims based on filenames or private material.

Claims are graded by the [public-only capability index](PUBLIC_CAPABILITIES.json); an unverified private project never counts as public executable evidence.

## Portable public-only project starters

[Source-pinned starter exporter](../tools/export_public_starter.py) selects original public samples by a finite allowlist; [unit and runtime tests](../tools/test_export_public_starter.py) verify copied bytes, reproducibility, source drift rejection, historical opt-in and non-overwrite. [Adaptation guide](TRANSFERABLE_WORKFLOW.md) describes translating generic patterns to a new workplace without importing private code. Export is not test execution, build qualification, a legal redistribution grant or a production deployment.

## Tenant authorization and audit records

Public proof: [tenant-policy implementation](../examples/tenant_policy/policy.py)
and [32 dedicated tests](../examples/tenant_policy/test_policy.py).
Synthetic policy evaluation, observational HMAC evidence and noncanonical
tamper rejection are demonstrated. Login, IAM, deployed tenancy and
production security review remain not verified.

## Transaction journals and reusable engineering recipes

The [independent ledger](../examples/atomic_ledger/ledger.py) and its
[31-case regression suite](../examples/atomic_ledger/test_ledger.py)
demonstrate atomic zero-sum postings, bounded integer amounts, conflict-safe
idempotency, concurrent writers, and balance/journal reconciliation.

[Public recipes](PUBLIC_RECIPES.md), the [composer](../tools/compose_public_solution.py)
and its [tests](../tools/test_compose_public_solution.py) select only
allowlisted public profile groups without employer source or automatic
deployment. Production financial/authentication systems remain unverified.
