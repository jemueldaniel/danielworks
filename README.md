# DanielWorks — engineering through runnable evidence

**Latest integration status: NOT GREEN.** An earlier complete Windows run passed 145 behavioural tests, but the subsequent integrated rerun stopped after 73 passes and one HTTP-test error (`test_content_type_size_origin_and_host`, WinError 10053 while expecting 415). No remaining command group is marked passed for that later run. The new verifier's standalone platform results remain separate. [Retained Windows receipt](verification/checkpoint-2.json).

**Authoritative destination:** [jemueldaniel/danielworks](https://github.com/jemueldaniel/danielworks). This candidate does not include or change the personal website or its form application. Source preparation is not evidence of publication; see the [delivery status](docs/COVERAGE_MATRIX.md#delivery-gates).

Start with the **[evaluation workbench](projects/evidence-workbench/README.md)**: one persistent workflow with two complete interfaces, not a collection of disconnected technology snippets.

| Working path | Read the implementation | Inspect the proof |
|---|---|---|
| **MCP integration:** official Streamable HTTP server → typed client → real tool execution → database | [Transport and session boundary](projects/evidence-workbench/src/server.ts), [tools](projects/evidence-workbench/src/mcp.ts), [typed MCP client](projects/evidence-workbench/src/mcp-client.ts) | [Wire and SDK tests](projects/evidence-workbench/tests/protocol.test.mjs), [capacity and confirmation tests](projects/evidence-workbench/tests/review.test.mjs) |
| **Persistent application:** React → typed HTTP SDK → Python HTTP → SQLite FTS5, durable work and inspectable results | [Interface](projects/evidence-workbench/web/App.tsx), [SDK](projects/evidence-workbench/src/api-client.ts), [storage/worker](projects/evidence-workbench/backend/workbench.py) | [Actual Edge browser flows](projects/evidence-workbench/tests/browser.test.mjs), [process-crash recovery](projects/evidence-workbench/backend/test_process_recovery.py) |

The retained Windows record tested the joined flow: **queue in the browser, execute through MCP, inspect the persisted evaluation, restart the backend and recover the same result.** Those network/browser results belong to that earlier source and environment; current cross-platform acceptance remains unresolved. The UI retains an uncertain submission, inspects its key, and never silently retries a write. The six-document synthetic corpus deliberately includes a retrieval failure.


**Latest bounded repair:** the [in-process agent example](examples/mcp_agent/README.md) now keeps its starting server and checkpoint store across suspension. Its 27-test suite preserves the earlier 24 cases. Fresh applicable Linux integration checks record **151 passes and one Windows-only skip**, not a new locked workbench/browser or cross-platform acceptance. [Current results and remaining gates](docs/CURRENT_VERIFICATION.md#current-run-context-repair--8-october-2026).

## Rust language implementation

The **[bounded Rust language](projects/bounded-lang/README.md)** adds a separate, dependency-free language pipeline: lexer → precedence parser → AST → resolved stack IR → VM. Repeated bindings intentionally shadow earlier values without reusing local slots. The regression first reproduced both an `UnknownName` failure and an incorrect result of `14` instead of `9`; the corrected implementation and its compiler/runtime resource limits passed **18 tests**, formatting and clippy in the retained record. Those Rust commands were not freshly rerun in the latest continuation. A separate reviewer verified the exact eight Rust files and found no blocking defect; two low-severity observations are explicitly recorded in [review status](docs/REVIEW_STATUS.md).

This is not a type checker, serialized bytecode format or production sandbox. The original four pipeline integration tests and two unit tests remain intact.

## Run it

Use the [exact setup, three-terminal run instructions and test commands](projects/evidence-workbench/README.md#setup-and-run). The retained Windows workbench record identifies Node 24.15.0, Python 3.13.6, SQLite 3.50.4 and Edge 154.0.4258.53. That historical isolated installation used `npm ci --offline --ignore-scripts --no-audit --no-fund` with an existing cache, followed by `npm test`; it is not a fresh or cold installation. The reconnected bridge reports Node 24.15.0/Python 3.13.6, but no new admitted Windows run or locked workbench build was completed. The latest Linux checks used Node 22.16.0. See [current versus historical version evidence](docs/CURRENT_VERIFICATION.md). Browser binaries are never downloaded automatically.

## Preserved foundations

The original **[durable queue](examples/durable_jobs/README.md)**, **[ranking grader](examples/ranking_eval/README.md)** and **[bounded TypeScript read client](examples/read_client/README.md)** retain their original implementations and all tests. The only original test change closes two fixture-owned SQLite connections explicitly after a clean Windows restore exposed a cleanup error; no assertion or test was removed. The workbench imports their behavior rather than duplicating it. The earlier supplementary exercises are preserved and [classified by their actual limits](docs/COVERAGE_MATRIX.md), not promoted into extra production projects.

See the **[skills-to-evidence index](docs/SKILLS.md)**, **[verification record](docs/TEST_EVIDENCE.md)** and **[architecture and tradeoffs](projects/evidence-workbench/docs/DESIGN.md)**.

**Limits matter:** permission profiles are synthetic, not login/authentication; SQLite is not PostgreSQL; this is MCP, not WebMCP; there is no model training, live EVM, distributed cluster or deployment claim. These are AI-assisted demonstrations, not proof of sole human authorship. [Authorship and redistribution boundaries](docs/PROVENANCE.md).

## Reproduce every preserved suite

From the repository root, use already installed Python, Node and a TypeScript compiler for the original examples. `tools/verify.py` deliberately neither installs nor deploys anything. The workbench has its own exact npm lock; do not confuse its TypeScript version with a global compiler.

```sh
python -B tools/verify.py
python -B -m unittest discover -s examples/typed_api_sdk -v
node --test examples/mcp_agent/test_runtime.mjs
python -B -m unittest discover -s examples/tx_sim -v
(cd examples/retrieval_lab && python -B -m unittest -v test_retrieval.py)
python -B -m unittest discover -s projects/evidence-workbench/backend -v
npm ci --ignore-scripts --no-audit --no-fund
npm test
cargo test --manifest-path projects/bounded-lang/Cargo.toml --locked --offline
cargo fmt --manifest-path projects/bounded-lang/Cargo.toml -- --check
cargo clippy --manifest-path projects/bounded-lang/Cargo.toml --locked --offline --all-targets -- -D warnings
```

The parenthesized `cd` command is POSIX shell syntax. On PowerShell, enter `examples/retrieval_lab`, run the Python command, then return to the root. This lexical exercise resolves its fixture relative to its documented working directory; a root-directory invocation was recorded as a failure, not quietly counted as a pass.

**Inspection map:** [single capability/backlog matrix](docs/COVERAGE_MATRIX.md) · [architecture](projects/evidence-workbench/docs/DESIGN.md) · [interface contracts](projects/evidence-workbench/docs/INTERFACES.md) · [current verification](docs/CURRENT_VERIFICATION.md) · [recovery and preservation](docs/RECOVERY.md) · [dependency/licensing boundaries](docs/DEPENDENCIES.md).

No workflows, runners, Pages setup, deployment definitions, cloud resource creation, credentials or vendored dependency binaries are part of this candidate. Nothing in these instructions authorizes a production deployment or a contract transaction.

## Source verification before installation

[Read-only checkout verifier](tools/verify_source.py) and [28 filesystem regressions](tools/test_verify_source.py) make the preservation checks runnable. Start in a quiet, isolated source-only tree, before dependencies or build outputs exist:

```sh
python -B tools/verify_source.py
python -B -m unittest discover -s tools -p test_verify_source.py -v
```

Use `--expected-manifest-sha256` with the exact manifest hash from a separately trusted delivery receipt to authenticate the manifest. Without that argument, a pass establishes internal consistency only. This does not establish authorship, independent review, runtime qualification or publication. The manifest excludes its own hash explicitly. [Format, limits and platform qualifications](docs/SOURCE_VERIFICATION.md).

**Historical checkpoint:** the recovered baseline's 145 behavioural cases were rerun on Windows; the 102 applicable Linux cases overlap that baseline and are not additional unique coverage. The new verifier has 28 distinct test definitions: 25 passed and three were skipped on Windows; 27 passed and one Windows-only case was skipped on Linux. The NTFS junction regression failed before the reparse-point fix and then passed. Neither repeated runs nor skips inflate the count. [Retained qualification receipt](verification/checkpoint-2.json).

Publication also requires resolving and requalifying that integration failure, applicable final-file independent review and repository trigger/settings evidence. No new GitHub commit, complete remote-file readback or GitHub restoration is claimed by this candidate. The checkpoint is not completion of the requested delivery.
