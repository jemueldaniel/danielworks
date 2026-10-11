# Persistent evaluation workbench

Two interfaces share one real workflow: an official-SDK MCP integration and an interactive React application. Both cross a Node HTTP boundary and a separate Python HTTP process before reaching the same disk-backed SQLite database. No injected fetch bridge stands in for the normal transport or database.

## Setup and run

Verified Windows toolchain: **Node 24.15.0 / npm 11.13.0, Python 3.13.6 / SQLite 3.50.4 with FTS5, Edge 154.0.4258.53**. Python backend tests also pass on Python 3.13.5 / SQLite 3.46.1 in Linux. Other browser engines and operating-system combinations are unqualified. Node 22.16 is the declared source compatibility floor, not a separately verified workbench runtime.

From the candidate root, with these tools already installed:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run typecheck
npm run build
```

There are no pip dependencies. The lock pins MCP SDK 1.32.1, React/React DOM 19.3.0, Zod 4.6.5, TypeScript 7.0.2, esbuild 0.28.2 and Playwright 1.63.0. Windows PowerShell may require `npm.cmd` instead of `npm`; use `python3` instead of `python` where appropriate. Install only tools and public dependencies admitted in your environment.

**Terminal 1 — real backend and explicit new, disposable database:**

```sh
python -B projects/evidence-workbench/backend/server.py serve --db .local/workbench.sqlite3 --port 8766
```

Do not point this example at an existing or production database. The server prints a ready record and creates the parent directory only for this explicit path.

**Terminal 2 — gateway, MCP server and React assets:**

```sh
node projects/evidence-workbench/dist/server.js http://127.0.0.1:8766/v1/ 8765
```

**Terminal 3 / browser:** open `http://127.0.0.1:8765`. Queue an evaluation, choose **Work next run**, inspect a result, cancel a pending run, or search the corpus. A worker invocation processes at most five cases; no unattended worker is started. Use Ctrl+C to stop each server.

The example exposes `/mcp/reader`, `/mcp/operator`, and `/mcp/other-reader` on the same gateway. These are **demonstration profiles, not credentials**. Anyone able to reach the loopback server can select the operator route. Do not expose the ports to a LAN, tunnel or public network.

### Bounded error-response behavior

The Python HTTP handler drains only a small, unambiguously declared rejected POST body (maximum 8,193 bytes) after writing a 4xx reply, avoiding a premature close with those bytes unread. Malformed/oversized bodies are not drained. The existing real HTTP test still requires exact 415, 413 and 403 results; additional focused tests exercise drain bounds without socket probes. A fresh 28-test backend run passed on Linux and Windows, but the earlier intermittent Windows connection abort remains an unresolved historical observation, not silently erased.

## Real SDK interface

After starting the two servers, execute from the repository root:

```sh
node --input-type=module -e "import {WorkbenchMcpClient} from './projects/evidence-workbench/dist/mcp-client.js'; const c=await WorkbenchMcpClient.connect('http://127.0.0.1:8765/mcp/operator'); try { console.log(await c.submit({key:'study-run',engine:'fts5',k:2})); console.log(await c.workOnce(5)); console.log(await c.inspect('study-run')); } finally { await c.close(); }"
```

This is an explicit mutation, not an automatically retried operation. `workOnce` claims the next eligible job for the demo tenant, not a caller-selected job; use a fresh database for the sample. A repeated identical submission shares the same key; changed parameters for that key are rejected. A transport failure requires inspection, not blind replay. The command syntax is supplied for study; equivalent SDK execution is verified in `protocol.test.mjs`, not claimed as a separately captured shell run.

On a fresh dataset, a completed FTS5/top-2 result contains:

```json
{
  "state": "done",
  "checkpoint_count": 5,
  "result": {
    "schema": "ranking-report.v1",
    "k": 2,
    "query_count": 5,
    "macro_recall_at_k": 0.8,
    "mrr_at_k": 0.8,
    "resumed_cases": 0,
    "failures": [{"id":"q-synonym","relevant":["delta"],"retrieved":[]}]
  }
}
```

This is a selected-field excerpt, not the complete response. Full responses carry input and ranking digests. The numbers describe five synthetic queries, not model quality or a benchmark advantage. The lexical baseline also scores 0.8 on this fixture, while its known failure returns irrelevant zero-score ties rather than no matches.

## Verification commands

Run from the root unless a `cd` is shown:

```sh
npm test
```

This runs strict TypeScript/type assertions, the build, real HTTP/MCP/SDK/review tests and real installed-browser tests. It does **not** run Python or the preserved examples.

```sh
cd projects/evidence-workbench/backend
python -B -m unittest discover -p "test_*.py" -v
```

The backend suite uses real SQLite, real sockets, thread races and an actual child-process exit/restart. Certain fine-grained lease tests deliberately control the clock. From the root, the original suites use:

```sh
python -B tools/verify.py
```

That preserved runner requires an existing `tsc` on PATH. Its recorded baseline used TypeScript 5.8.3 and Node 22.16.0, separately from the workbench's locked compiler. See [the verification record](../../docs/TEST_EVIDENCE.md) for the exact environments and supplementary commands.

For the browser suite, set `BROWSER_PATH` to an **already installed, admitted** Chromium-family executable when it is not the default Windows Edge path. The tests do not fetch browsers. Linux container navigation was blocked by administrator policy and was not bypassed; the UI qualification was performed on Windows Edge instead.

## Read the execution paths

[MCP transport/session boundary](src/server.ts) → [tool registration and permission-specific catalog](src/mcp.ts) → [typed API SDK](src/api-client.ts) → [Python HTTP server](backend/server.py) → [storage and worker](backend/workbench.py).

[React interface](web/App.tsx) → the same HTTP SDK/gateway/backend/storage path. There is no second queue, grader or retrieval database for the browser.

Study [architecture, limits and failure semantics](docs/DESIGN.md), [tool and HTTP contracts](docs/INTERFACES.md), and [the mapping of tests to behavior](../../docs/COVERAGE_MATRIX.md).
