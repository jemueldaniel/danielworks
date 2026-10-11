> **Preserved earlier workbench record.** For this recovery/fix cycle, use [CURRENT_VERIFICATION.md](CURRENT_VERIFICATION.md). Earlier tool versions and commands below remain historical evidence, not newly rerun claims.

# Execution evidence — 7 October 2026

These are captured local results, not CI results, independent certification or production evidence. Original repositories were inspected read-only, not built. New code ran only in isolated example environments. Source identity is recorded in [the tested-source binding](../verification/tested-source-binding.json); package versions are captured in [versions.json](../verification/versions.json).

## Original three examples: fresh regression run

From the candidate root:

```sh
python3 -B tools/verify.py
```

Observed exit **0** on Linux: Python **3.13.5**, SQLite **3.46.1**, Node **22.16.0**, TypeScript **5.8.3**. The original runner was not changed and requires an already installed `tsc` on PATH. It is a separate toolchain from the locked workbench build.

| Original check | Actual result | Scope |
|---|---|---|
| Durable jobs | 17 passed | Temporary real SQLite databases, concurrent connections, rollback/lock/reopen tests; controlled-clock cases are synthetic |
| Ranking grader | 15 passed | Synthetic fixtures, strict schema and metric checks, actual CLI subprocesses; not a model run |
| TypeScript | Compilation passed | Strict compiler and positive/negative compile-only type assertions |
| Bounded read client | 28 passed | Mostly controlled transports/streams, plus an actual loopback HTTP integration |

The **60 original behavioral tests passed freshly**, rather than inheriting an old claim. [Captured result](../verification/original-60.json). Original example source, fixtures and tests are byte-identical to the previous delivered candidate; the accompanying review pack includes the preservation manifest. Counts are bookkeeping, not coverage or expertise scores.

## Real workbench: clean install and complete Node/browser suite

Executed in the isolated Windows candidate using Node **24.15.0**, npm **11.13.0**, Python **3.13.6**, SQLite **3.50.4**, and the installed **Microsoft Edge 154.0.4258.53**:

```powershell
npm.cmd ci --ignore-scripts --no-audit --no-fund --registry=https://registry.npmjs.org --fetch-retries=0 --fetch-timeout=15000 --maxsockets=4
npm.cmd test
```

Both commands exited **0**. The clean install was followed by another complete test pass, not merely reuse of an earlier build. [Install transcript](../verification/clean-install.txt) · [Complete clean-install test transcript](../verification/clean-install-tests.txt).

`npm test` actually expands to:

```sh
npm run typecheck
npm run build
node --test --test-concurrency=1 projects/evidence-workbench/tests/protocol.test.mjs projects/evidence-workbench/tests/api.test.mjs projects/evidence-workbench/tests/review.test.mjs
node --test --test-concurrency=1 projects/evidence-workbench/tests/browser.test.mjs
```

Strict **TypeScript 7.0.2** passed; **esbuild 0.28.2** built both Node modules and the React interface. The network suite passed **18** cases using actual HTTP sockets, official MCP client/server transports, a separate Python process and real SQLite files. The browser suite passed **7** cases, including two viewport sizes: **1280×800** and **390×844**. A mobile-size viewport is not a physical-device test.

| Boundary | Executed behavior |
|---|---|
| Protocol and permissions | MCP initialization and pinned protocol negotiation; real tool schemas/execution; required sessions; profile/session binding; reader mutation denial; invalid input/unknown tool rejection |
| Capacity and message limits | 16-session capacity and real DELETE reclamation; stale session rejection; forbidden origins, oversized requests, batches and media-type rejection |
| SDK write safety | Concurrent same-key submissions; changed-body conflict; caller tenant injection rejection; pre-aborted calls not sent; bounded responses; no automatic mutation retry; a schema-valid wrong-operation response rejected |
| Backend recovery | Backend process stopped, then restarted on the same database; MCP reads recover rather than inventing success |
| Joined browser/MCP path | Queue in React, execute through MCP, inspect persisted output in React, observe backend loss and recover after restart |
| Browser usability | Keyboard form interaction; narrow-layout overflow checks; native modal Escape/focus restoration/background inertness; loading/disabled states; durable mobile cancellation and reload |
| Browser uncertainty | A real POST commits before its response is deliberately dropped; saved key is inspected without duplicate write. Offline submission survives reload and requires explicit same-key retry. Invalid saved requests cannot become writes |

Fault injection deliberately delays or drops a response after/before an actual network operation. This is not a mock replacing the normal persistence path. Tests exercise real engines; they do not constitute full protocol conformance or a full accessibility audit.

## Python backend, concurrency and crash recovery

```sh
cd projects/evidence-workbench/backend
python -B -m unittest discover -p "test_*.py" -v
```

Observed exit **0**, **26 passed**, on both Windows Python 3.13.6/SQLite 3.50.4 and Linux Python 3.13.5/SQLite 3.46.1 (`python3` on Linux). [Windows transcript](../verification/backend-windows.txt) · [Linux transcript](../verification/backend-linux.txt).

This suite includes actual FTS5 retrieval and the preserved grader; concurrent submissions and workers; tenant partitioning in SQLite; stable pagination; cancellation fencing; corrupt-checkpoint rejection; closed-connection regression; malformed/duplicate JSON; real HTTP boundaries; unknown schema and input identity rejection. The process test exits a child after its first committed checkpoint, waits for an actual lease expiry, resumes in another worker and checks terminal no-replay. Other lease tests deliberately control time. No power-loss or multi-host claim follows.

## Earlier supplementary exercises

These exact commands were rerun; they are not the new vertical integrations:

```sh
# Run this one from its own directory: its preserved test reads a relative fixture.
cd examples/retrieval_lab
python3 -B -m unittest -v
# Return to the candidate root for the remaining commands.
cd ../..
python3 -B -m unittest discover -s examples/typed_api_sdk -p 'test_*.py' -v
python3 -B -m unittest discover -s examples/tx_sim -p 'test_*.py' -v
node --test --test-concurrency=1 examples/mcp_agent/test_runtime.mjs
```

Results: lexical baseline **3 passed**; Python API-contract exercise **4 passed**; Python transaction simulation **4 passed**; in-process MCP/workflow simulation **5 passed**. The first retrieval invocation used the wrong working directory and failed to locate its fixture; its raw failure was retained privately. The correctly scoped command passed without changing the original tests. Do not interpret the simulations as real MCP, Solidity or EVM execution.

## Failed evidence preserved and corrected

The private review pack preserves both failing and passing transcripts, including initial missing-implementation tests, the SQLite connection leak, strict SDK declaration/ambient-type errors, an unrelated parent package-manager resolution problem, a Windows child cleanup hang, and the wrong-operation confirmation regression. The latter was demonstrated failing before the correction and then passing with real sockets. The process cleanup issue was stopped within the owned test process tree and fixed before rerunning. A browser attempt in the Linux container was blocked by administrator policy; that policy was not bypassed. Windows Edge supplied the admitted browser evidence instead.

The same assistant authored and self-reviewed this work. Black-box tests are separately defined behavior checks, **not a second reviewer**. Independent human/agent review remains outstanding.

## Dependency check, packaging and unrun checks

```powershell
npm.cmd audit --json
```

Observed exit **0**, **zero known vulnerabilities reported** for the installed lock at the time of this run. [Raw audit result](../verification/dependency-audit.json). This is not proof of absence of vulnerabilities. No `audit fix`, workflow change or dependency update was applied.

[Sample output](../verification/sample-output.json) comes from actual execution against the synthetic fixture. Dependency and runtime versions are in [DEPENDENCIES.md](DEPENDENCIES.md). The source archive excludes dependencies, built outputs, database files, private logs and Git history. It requires the documented install/build steps before running.

**Unrun / unqualified:** WebMCP browser-native tools, Next.js/SSR, Safari/Firefox/screen readers/physical mobile hardware, full wall-clock session expiry, PostgreSQL/RLS, a replicated queue, compiled Solidity/EVM, Rust or a new public compiler, training/GPU/distributed training, production auth, load/performance, deployment, release signing and CI. A declaration or source file is not substituted for these checks. No runner or deployment was triggered.
