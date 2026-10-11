## Public-only one-command assembly candidate — 11 October 2026

This revision adds `tools/one_shot_public_project.py` and `tools/test_one_shot_public_project.py` as a **complement** to the existing public starter exporter and independent output verifier. An externally pinned source manifest is mandatory; output bytes are checked before and after fixed local test execution. Child tests run with a restricted allowlist of portability variables rather than the entire ambient process environment. A separate receipt is never overwritten or stored inside the kit. Failure leaves the exported data inspectable and is not a success claim. Test results attach to the exact revision, and historically qualified profiles remain historical even if a local example passes today. Whole-package independent security/licensing review, locked browser/npm build, real cloud, PostgreSQL, EVM and distributed training qualifications are still outstanding.

## Independent exported-kit integrity and runtime acceptance — 11 October 2026

Fresh public-only code adds `tools/verify_exported_starter.py` with `tools/test_verify_exported_starter.py` and improves the existing public exporter **without duplicating it**. It requires a separately stored output-manifest SHA-256, detects changed, unlisted, missing, linked or case-colliding material, and runs only hardcoded per-profile test commands. The manifest's manually documented commands are never executed. Synthetic educational examples and historical qualification limitations remain unchanged. Test counts and source pin for the new commit are recorded externally after execution. Whole-package independent review, browser/locked dependencies and live cloud/contract qualifications remain unverified.

# Current verification — 11 October 2026

## New public-only training and capability-evidence candidate — 11 October 2026

The public repository was checked at the **110-file `da94ab6378c6465b17bdaaf5f8bccf82eef645e1`** checkpoint before this work. The following candidate is separately authored and must be assigned its own Git commit and external manifest receipt before it counts as publication.

New, public-only original files:

- `examples/synthetic_training/training.py`, `demo.py`, `test_training.py` and `README.md`: actual bounded CPU logistic-regression learning on generated toy data. **17 tests passed on Linux Python 3.13.5**, including a red-then-green forged-completion regression. No user data, private code, model service, live GPU/LLM or cloud deployment.
- `docs/PUBLIC_CAPABILITIES.json`, `tools/verify_public_capabilities.py`, `tools/test_verify_public_capabilities.py`: public-only evidence links, explicit not-verified rows, and **13 claim-validation tests passed**. Structural checks do not re-execute the linked tests or certify private engineering.

The private-source comparison was read-only and its exact paths, histories and content are excluded from public source, logs and preserved published receipts. Historical 8 October and earlier records below remain attached to their own source revisions, not rewritten as present-day test runs. Full-package independent review, Windows qualification of the new training example, Rust toolchain and locked web/browser integration must be reported separately.


## Node 22 and 24 compatibility — 11 October 2026

**Actual defect and repair:** the 109-file public commit `f811ecf09481ebe4d225620e1131753f1dd85b79` contains the existing `tools/verify.py` example-suite wrapper. An isolated Windows clone of that commit ran the 28 SDK tests successfully under **Node 24.15.0**, yet its wrapper reported `SDK FAIL / tests null` and exited 1 because it depended on older Node TAP text while Node 24 selected the newer spec output. That failed execution is retained as a fresh observation, not silently converted into a pass. The correction explicitly invokes `node --test --test-reporter=tap`; `test_result` also validates reported count, passed count, failed count and process exit before giving `PASS`. It does not turn failed tests into success by ignoring process status.

**Test-first evidence:** the new `tools/test_verify_runner.py` asserts the SDK CLI requests TAP. It failed against the older wrapper and passed after the correction. Six distinct tests also cover Node 22 TAP, Node 24 spec, reported failure, nonzero exit, missing/zero test totals, and the actual CLI selection. On Linux (observed **Node 22.16.0**, **Python 3.13.5**) six runner regressions and the 28 SDK tests passed; the original verifier's three groups passed **60/60**. On Windows (observed **Node 24.15.0**, **Python 3.13.6**, existing **TypeScript 5.9.3**) six runner tests passed, the 28 SDK tests passed, and the full original queue/grader/SDK wrapper passed **60/60**. These original definitions overlap the prior 60-case baseline and are not new cases. The six runner definitions are new.

**Scope:** this establishes original-example compatibility with those existing Node/TypeScript/Python installations, not successful cold installation or build of the exact locked workbench (TypeScript 7.0.2, MCP 1.32.1 and browser cases). No dependency changes, browser installation, external services or deployment occurred. The manifest for the new unpublished-at-edit-time candidate is regenerated; its source SHA-256 and future publication SHA belong in a separate readback receipt. Whole-package independent review is incomplete. Earlier HTTP WinError 10053 evidence is preserved despite successful subsequent 28-case Windows backend runs.

## 11 October 2026: published baseline and current candidate

The first full checkpoint **is published** at [commit `082086d4`](https://github.com/jemueldaniel/danielworks/commit/082086d4c64ed24db5a6ef8288b7517e3582668e), tree `8d0ca5fea7096b7cdccad2a7b39e1847cfcd66c9`. The 107 public files were each read from that commit and compared for byte length and SHA-256. A separate Windows clone from GitHub, with `core.autocrlf=false` local to the checkout, was clean and verified 107/107 files against externally pinned manifest SHA-256 `282b77b1b10bae52845bc4b244dc364cd515043d09d3257573a263d271be65f3`. This does not certify the application runtime.

New follow-up source changes (not part of that pinned baseline):

- `projects/evidence-workbench/backend/server.py` consumes a complete *bounded* rejected POST body after sending an error response and before connection close, provided there is exactly one valid Content-Length, no Transfer-Encoding and at most 8,193 bytes. The normal successful body is never consumed twice; oversized/ambiguous requests are not drained. This is a bounded mitigation for unread-payload close behavior, **not proof of the original WinError 10053 root cause**. The actual HTTP 415/413 status assertions remain intact.
- `projects/evidence-workbench/backend/test_http.py` adds two focused tests exercising the previously absent drain and its bounds. Before implementation, one new test had three failing subcases; the other negative test passed. After implementation both pass, with the unchanged existing tests.
- `tools/verify_git_commit.py` verifies the *committed* Git blob inventory, actual SHA-256/byte sizes, modes and manifest pin without contacting the network or modifying source. It reports working-tree cleanliness separately; checkout-byte qualification still requires `verify_source.py`. Nine offline local-Git fixture tests pass, including malicious/missing members and conflicts.

**Fresh backend execution:** Python 3.13.5 on Linux: 28/28 passes; Python 3.13.6 on the authorized Windows laptop: 28/28 passes, including `test_content_type_size_origin_and_host`. Windows execution used an isolated checkout with the exact same two modified Python files (matching SHA-256), after confirming 5.658 GiB free memory. The historically recorded intermittent WinError 10053 is retained: one succeeding rerun is not permanent fault elimination. The held standalone socket probe and Rust-version query were not repeated.

**Fresh Git-verifier execution:** nine local-fixture tests passed on Linux **and nine on Windows**, without network, installs or remote Git writes. On the modified isolated Windows validation checkout, the tool also verified all 107 raw Git objects of the previously published commit and the externally pinned original manifest while correctly reporting that the working directory contained candidate modifications. The newly modified manifest must be externally pinned after integration and verified again after publication; no future commit identity is embedded in the source. These tests are separate from the earlier 151 disjoint Linux passes (and one skip) recorded below. The complete locked npm/TypeScript/browser suite and Rust checks were not established by these two changes.

**Review and release limits:** no fresh independent whole-package approval, no production endpoint or deployment, no PostgreSQL/EVM/training/native WebMCP qualification, and no claim of zero external trigger integrations. Publication is a disclosed incremental engineering checkpoint rather than full product certification.

## Current run-context repair — 8 October 2026

**Whole-package acceptance remains incomplete; zero new GitHub commits.** The starting source was the exact 107-file Library-backed agent-recovery candidate, archive SHA-256 `d33aae2088ed540d19a62adb5a763d8c585c8f1976bb3de02bfd6e61551ddff3` and externally pinned manifest SHA-256 `8058dc206c5c2da680d482ecc517d20bb4952995a963d57e5bed643c249f3740`. It was restored separately before these changes. Old receipts and first-repair/failure evidence remain unchanged.

The runner previously read its public `server` and `store` fields again after awaiting a tool. Reassigning those fields could route a later step to another server or write its checkpoint into another Map. Each invocation now captures its starting server and store for calls, checkpoint access, shared-Map exclusion and cleanup. Live caller permission revocation remains checked between steps. This is reference stability, not authenticated storage, immutable tool implementations, distributed exclusion or exactly-once effects.

The full module passed **27 distinct tests**: all **24 earlier** definitions remain unchanged and **three additional** cases cover suspended store reassignment, suspended server reassignment and JSON-serialized partial-checkpoint continuation after cancellation. Before the fix, the expanded suite had 25 passes and two failures; after it, 27 passed. The partial-checkpoint case passed before the change and expands coverage; it is not a third repaired defect. Repeated executions are not additional test definitions.

### Fresh integrated Linux checks

| Scope | Result | Actual qualification |
|---|---:|---|
| Original queue, grader and bounded read SDK | 60 passed | Temporary SQLite, synthetic grading datasets, controlled transports and one loopback HTTP test; original SDK strict compilation with existing TypeScript 5.8.3 |
| Python contract, lexical retrieval and transaction exercises | 11 passed | Five contract cases, three retrieval cases and three Python transaction-simulation cases; not HTTP authorization or EVM |
| In-process agent exercise | 27 passed | Real example implementation with synthetic tools; RAM-only Maps and process-local concurrency |
| Python workbench backend | 26 passed | Actual loopback HTTP, disposable SQLite/FTS5, threads and child-process recovery on Linux |
| Source verifier | 27 passed; one skipped | 28 distinct filesystem cases; NTFS junction case is Windows-only and was skipped explicitly |

This is **151 passes** and one Windows-only skip across 152 distinct applicable definitions. These groups are disjoint; the same agent tests executed before/after repair or on restoration are not added twice. Earlier 129-pass Linux and 145-case Windows baselines remain historical rather than extra passes. Documentation assertions and source-inventory checks are reported separately, not added to behavioural coverage.

Observed Linux toolchain: Node 22.16.0, Python 3.13.5, SQLite 3.46.1 and existing TypeScript 5.8.3 for the original SDK only. This **does not qualify Node 24.15.0** or the workbench's locked TypeScript 7.0.2. Jobs ran serially after a measured 2 GiB container-headroom check; this check is not a separate OS reservation. No dependency installation, browser download, Rust version probe, EVM/contract action, infrastructure start or external service call was part of these tests.

### Windows, dependencies, review and delivery

The **Windows device is online** and its connected bridge reports Node 24.15.0 and Python 3.13.6. Read-only source/status operations succeeded through the existing admission mechanism. However, no admitted **standalone showcase workspace** with a valid source/worktree and claim binding was established. The available builder setup is tied to private product source; it was not repurposed or modified for this showcase. This is not an offline-device claim or evidence that the Windows acceptance run passed.

The preserved Windows `test_content_type_size_origin_and_host` error, WinError 10053 while expecting HTTP 415, remains unresolved. Its handler, assertion and SQLite connection fix are unchanged. Early response before body consumption remains a hypothesis, not established cause. Neither held socket diagnostics nor the held Rust-version query was retried. The 25 locked network/browser cases and 18 Rust cases were not freshly run. No full `npm test`, locked workbench build or clean Windows install is claimed.

The exact locked zod-to-json-schema 3.25.2 object was absent from the inspected content-addressed caches. No relevant registry prerequisite was established as changed, so no network retry or install was attempted. Prior offline-install, DNS and EAI_AGAIN failure evidence stays preserved. No dependency version or lockfile changed.

**No new independent review** has completed. Current discovery exposes no callable independent-review executor in the security integration; local scheduler/command execution is not an independent code reviewer. The eight-file Rust static review is retained only because every input hash still matches, with both low-severity observations intact. Full-candidate correctness, privacy and licensing approval is still missing.

GitHub blob/tree/commit creation and non-forced expected-tip ref update remain available. The separate complete Actions policy, hooks, all relevant Apps/access/events, external build/deployment and branch-requirement inventory remains incomplete. No test push, branch, PR, Git object or ref update was used to discover effects. A saved local/Library restoration is not a clean restoration from a published showcase commit.

Only the existing agent runtime and test file change execution inputs; the other 56 of 58 execution inputs are unchanged. Root navigation is retained, with stale current-run wording corrected. There is one authoritative source manifest and one coverage matrix. The manifest excludes itself; its final hash and any future publication commit belong in an external receipt.

## Earlier 8 October agent-recovery record — historical

The following record describes the earlier 24-test repair, its then-offline environment and its own source hashes. It is retained as history, not the current connection or qualification state.

## New unpublished agent-recovery repair

**Whole-package acceptance remains incomplete.** This continuation recovered the exact latest 107-file documentation-corrected candidate and preserved its original bytes before creating this repaired candidate. The sole runtime change is the existing in-process agent runner and its regressions. This is not a repair or clearance of the Windows HTTP failure.

The full affected module command was:

```sh
node --test --test-concurrency=1 examples/mcp_agent/test_runtime.mjs
```

It passed **24 distinct tests**: all five original cases and **19 new** cases. They cover request/permission identity, corrupt and incompatible checkpoints, recorded progress/results, snapshot alias isolation, caller mutation during an awaited tool, same-Map concurrency, independent run IDs, explicit retry after a tool failure, live permission revocation, cancellation, bounded JSON and JSON-serialized checkpoint restoration. This is the real in-process implementation with synthetic tools, not a network/native protocol or durable-store integration.

The initial red run was 7 passes / 12 failures across 19 cases against the old runtime. After the first repair, 19/19 passed. Coordinator self-review identified a permission-revocation regression; the expanded run was 23 passes / one failure across 24 cases. The final correction passed 24/24. Executions overlap: these are **24 unique final test definitions**, not a sum of those runs. Failed output and first-patch bytes remain in the private preservation evidence.

No independent review of this agent repair has completed. All eight Rust review hashes still match, but that scoped static review does not approve these JavaScript/documentation changes or the whole candidate. The three prior Rust regression additions and both low-severity review observations remain unchanged.

### Environment and blocked checks

Observed environment: Linux, Node **22.16.0**, Python **3.13.5**, 4 GiB container memory limit and four CPU equivalents. One coordinator executed jobs serially with a 2 GiB memory reserve; no independent workers were active. The repository's `.node-version` remains **24.15.0**. The Node 22.16.0 run is **not a qualification of the pinned Node version**.

No dependency was installed and no browser or toolchain was downloaded. The workbench's exact-lock dependency cache is incomplete. Its `npm test` chain (locked TypeScript, build, network and browser checks) was therefore not invoked with a substitute compiler or partial install. The 25 network/browser and 18 Rust cases are not fresh results. Unchanged passing application groups were not rerun.

The Windows device/local bridge is unavailable. The preserved Windows test still expects 415 and its WinError 10053 remains unresolved. No denied socket probe or blocked Rust-version query was repeated, and no handler/assertion patch was made. Linux agent tests do not clear Windows acceptance.

### Source and delivery boundary

The source manifest is regenerated for this new candidate. Exactly two of the 58 execution inputs change: `examples/mcp_agent/runtime.mjs` and `examples/mcp_agent/test_runtime.mjs`; the other 56 match the recovered corrected checkpoint. Historical receipts below retain their original hashes and do not claim to test the newer runner. All 107 paths remain present.

GitHub publication primitives are exposed, but the reviewed-allowlist, complete side-effect inventory and applicable acceptance gates remain open. No GitHub content was written by this continuation. Local source restoration is not a clean restore of a published candidate. No publication, deployment, cross-platform completion, privacy/license clearance or native capability acceptance is inferred.

## Historical 7 October report — immutable observations for its own source

The remaining sections retain the earlier report. “Current,” “fresh,” “final,” and its tested-source bindings below refer to that earlier execution, not to the newer agent-recovery candidate. Its 145-case result, later Windows failure, overlapping Linux executions and earlier cache installation remain distinct historical evidence.


## Later recovery run — 7 October 2026

The retained record below describes the earlier checkpoint. A fresh isolated Windows run subsequently passed the same 145 distinct cases, checks/build, Rust formatting and clippy. All 56 execution-affecting hashes were reconciled. The applicable Linux 102-case suite also passed. The standalone new source checker passed 25 Windows cases (three skips) and 27 Linux cases (one skip).

**The latest integrated Windows rerun is not green:** 73 passed and one backend HTTP case errored, after which remaining groups were not run. The repeated diagnostic probe was blocked. Six disjoint reviewer processes were attempted after the formerly stated quota-reset time; all returned usage-limit errors with zero report bytes. No new review approval, publication, remote-file qualification or GitHub restoration resulted. See the [immutable fresh-run receipt](../verification/checkpoint-2.json) and [single current backlog](COVERAGE_MATRIX.md). Earlier receipts were not edited to conceal this failure.

This record describes **actual execution in this recovery/fix cycle**, not inherited passes or CI. The full local source was restored into a second isolated directory before installation. That restore was from the verified local candidate, **not from GitHub**; no candidate commit has yet been published.

## Final executed checks

The clean local restore passed **145 distinct behavioural tests** and its compiler/build checks. Linux reruns of the same tests are additional platform evidence, not extra unique tests.

| Component | Result | Actual execution boundary |
|---|---:|---|
| Original durable queue | 17 passed | Real temporary SQLite, concurrent connections, leases/retry/cancel/fencing/rollback; controlled clocks explicitly synthetic |
| Original ranking grader | 15 passed | Synthetic datasets, schema/metric validation and actual CLI subprocesses |
| Original bounded read SDK | 28 passed | Controlled transports and one actual loopback HTTP test; strict TypeScript/type assertions also passed |
| Python API/SDK contract exercise | 5 passed | In-process Python contract implementation, not HTTP or the newer TypeScript SDK |
| Prior tool/agent exercise | 5 passed | Explicit in-process simulation, not MCP transport |
| Transaction exercise | 3 passed | Python balance/intent simulation, not EVM |
| Lexical retrieval baseline | 3 passed | Actual local ranking against its fixture, from the documented working directory |
| Workbench Python backend | 26 passed | Disk SQLite/FTS5, actual TCP, threads, process exit/restart, cancellation and recovery |
| Workbench network suite | 18 passed | Actual HTTP, official MCP server/client transport, real SQLite backend and controlled fault injection |
| Workbench browser suite | 7 passed | Installed Edge, 1280×800 and 390×844, React/backend/MCP joined flow, keyboard/modal/mobile-width/error/response-loss/restart states |
| Rust language | 18 passed | Actual compiler/test execution, original pipeline and new binding/resource/error regressions; no dependencies |

The local restore ran **14 sequential command groups**, all exit 0 after the recorded fixture correction: the seven Python/Node foundational/backend groups; exact-lock install; original TypeScript compile; original SDK tests; full `npm test`; Rust tests; Rust formatting; Rust clippy. No test was skipped to obtain that result. Command output is preserved privately and selected sanitized execution records accompany this candidate.

## Dependencies and environment

The fresh Windows install command was:

```powershell
npm.cmd ci --offline --ignore-scripts --no-audit --no-fund
```

It installed 108 packages from the existing cache into an empty `node_modules` directory. The unchanged lock SHA-256 is `f389c35e449bc42227cd3113c0d14c948d82a9bd1fa97a455c8a4c273c2a9731`. No lifecycle script, browser download, new cloud resource or production deployment was run. This is offline reproducibility with an existing cache, not proof of future registry availability.

Exact lock declarations: MCP SDK **1.32.1**, React/React DOM **19.3.0**, Zod **4.6.5**, TypeScript **7.0.2**, esbuild **0.28.2**, Playwright **1.63.0**, `@types/node` **26.6.4**, `@types/react` and `@types/react-dom` **19.3.0**. These are inspected package/lock versions, not claims that they are the latest releases.

The current Windows bridge reports **Node 24.15.0** and **Python 3.13.6**. The actual current browser run reports **Edge 154.0.4258.53**. The preserved earlier record reports npm 11.13.0, SQLite 3.50.4, and Rust/cargo 1.95.0; those values are **historical**, not freshly verified by this cycle. A fresh omnibus version/help query was safety-blocked and was not retried or bypassed. Actual Cargo test/fmt/clippy execution succeeded, but a fresh exact Rust version remains a metadata gap.

The Linux preserved verifier was rerun after the queue-fixture fix: **Python 3.13.5, SQLite 3.46.1, Node 22.16.0 and TypeScript 5.8.3**, with all original 60 tests passing. The clean Windows restore additionally compiled the original SDK using the workbench's locked TypeScript 7.0.2 and passed its same 28 tests. No Linux browser or Rust execution is claimed.

## Failures retained, not erased

**Rust duplicate bindings:** before changing the compiler, the repeated-name regression failed with `UnknownName`; an initializer/shadowing/later-binding case returned 14 instead of 9. Both tests failed against the old source and pass against the corrected total-binding allocation.

**Rust local-count wrap:** 65,536 bindings were incorrectly accepted. A regression failed before checked allocation was added; it now receives `Overflow`.

**Rust compile/IR budgets:** all four new tests initially failed: oversized source, excessive nested expressions, excessive flat AST depth, and uncharged empty IR blocks. The 1 MiB source cap, 256-token statement cap and empty-block rejection corrected those cases without removing original tests.

**Windows queue fixture cleanup:** the first full local restore failed the existing rollback test with `WinError 32` when its temporary database was deleted. The test's two raw SQLite transaction contexts did not close their connections. The fix uses `contextlib.closing` around those same real connections while retaining transaction contexts, rollback checks and every original assertion. The queue implementation is unchanged. The test now passes on Windows and Linux. Original test SHA-256: `cb087528ddd1edbf47e57547dc8a7565949fd9a1faa64b2cdcc16338f3acd021`; corrected SHA-256: `251d949e9d110b4af1fa1e6695bdb30f312c9acab5f2b73c4642fb1b24d7a3be`.

**Retrieval invocation:** an initial root-directory test invocation failed to find its fixture. Its existing README already required running from `examples/retrieval_lab`; that command passed. The failed invocation is retained as a working-directory limitation, not a test that secretly passed.

## Not run, not inferred

No PostgreSQL integration, Solidity compiler/EVM target, WebMCP browser integration, model-training run, multi-node cluster, production authentication, external billing, cloud deployment, power-loss test or live funds movement was performed. A real local integration and deliberate failure injection are distinguished from mocks and simulations above. The single [coverage/backlog matrix](COVERAGE_MATRIX.md) records the exact remaining prerequisites.

There is no candidate GitHub commit to restore. Remote publication, complete remote byte readback and a clean recovery from the **published** revision are therefore not complete. Local restore evidence must not be presented as satisfying that remote-delivery requirement.

## Source binding and evidence handling

All **56 execution-affecting paths** in the final candidate match the actually tested Windows restore byte-for-byte. SHA-256 of compact sorted JSON mapping those paths to their SHA-256 values is `a9f919f6f9aecb9f981fed8517b094204a4ce54414b98096aac47690dec6dbdd`. The 86-path as-tested snapshot binding is `cb7365783ade58efc3c08522d0b43ffa8ee3375abea332808aad61eb2d2e286d`; subsequent changes are documentation/evidence only. Two historical evidence files were line-ending-normalized in the desktop text transfer; the final candidate retains their original workbench archive bytes.

[Captured clean-local-restore output](../verification/current/local-restore.json) records the 14 successful commands, original captured-output digests and sanitized outputs. [Tested source binding](../verification/current/tested-source-binding.json) records the exact program/fixture/lock set. Regression-red files in the same folder preserve failures. Public copies normalize Windows line endings and redact private diagnostic path prefixes; they are not represented as untouched private transcript bytes. Original private records remain separate.

The new Linux original-suite rerun produced a byte-identical summary to [the preserved canonical 60-test summary](../verification/original-60.json). Its duplicate copy is omitted; the current execution account above records the rerun without counting the same tests twice.

### Transferable starter extension (11 October 2026, next candidate)

A new dependency-free CLI exports allowlisted public examples to fresh directories, requiring a pinned source manifest and preserving qualification flags. Its own regression tests cover metadata drift, byte-for-byte output, non-overwrite and actual re-execution of selected public examples. Any new test pass count must be bound to its exact post-edit manifest and clean published checkout; earlier results for the 117-file checkpoint remain prior evidence rather than automatic certification. No private source was exported or used as input.

### 11 October 2026 Windows portable-starter acceptance correction

The clean public 121-file checkout passed source and raw Git object verification.
Its first portable-starter test run recorded 18 passes, one reporter-assertion
failure and two symlink-creation privilege errors (Windows WinError 1314). The
agent subprocess itself exited zero and reported 27 passing tests; the test
wrapper was matching a locale-dependent pretty-print prefix. The next candidate
requests deterministic Node TAP output and requires `# tests 27`, `# pass 27`,
`# fail 0`. The two link-creation tests explicitly **skip**, rather than pass,
when Windows does not authorize link creation; they still execute on systems
where links can be created. Current candidate tests must be freshly rerun.
This does not qualify an untested NTFS symlink rejection path on that host.

## New portable full-stack reference — independently testable local increment

New source `projects/portable-proof-studio/` adds an original Python standard-library loopback HTTP application backed by real SQLite files, plus a responsive browser UI. The suite contains **36 distinct tests** covering workspace partitioning, authenticated-demo token expiry, replay-safe transaction and concurrency, workflow revision errors, saved run/artifact identities, explicit cross-app import, document revision/deletion and lexical evaluation, process restart, HTTP origin/media guards and static UI contracts. The public one-shot exporter adds a sixth executed reference profile (`proof-platform`).

The first native Chromium navigation was **blocked with `ERR_BLOCKED_BY_ADMINISTRATOR`**. Do not interpret HTTP/markup tests as native-browser or accessibility acceptance. No private product source, cloud API, provider credential, EVM or payments were used. This addition is a local-only educational reference, not a deployed ten-application suite or a fully qualified locked workbench.

### Windows fixture follow-up — requires remote confirmation

The first published 134-file GitHub checkout passed source and Git-object byte verification on Windows but **failed four temporary-database cleanup tests** with `WinError 32`. The fixture had used `sqlite3.Connection` as a context manager, which commits but does not close the OS handle. The revised `managed_test_connection()` explicitly closes connections, with a new regression for immediate file deletion. The original failure remains recorded; this follow-up requires a fresh Windows test before a cross-platform claim.


## 11 October 2026 — new portable signed-event reference

A separate original Python reference was implemented in
`examples/event_outbox/`, isolated from the user's private product
workspaces. On the connected Windows machine, **33 distinct tests passed**
against its actual SQLite database, HTTP loopback server and threaded writer
races with Python 3.13.6. These 33 definitions do not count earlier recorded
tests and do not establish Linux coverage until executed there.

The new reference includes timestamp-bound HMAC signatures over exact
request bytes, byte-level idempotency and conflict handling, monotonic
worker lease generations, expiration, retry/dead-letter handling and durable
post-restart receipt readback. The source and demonstration signing key are
synthetic. It does not contact upstream providers.

This is local educational evidence only: no hosted listener, external
message broker, provider identities, key rotation, secret vault, full
network-facing threat model, external-effect exactly-once guarantee or
production security certification has been established. The prior workbench,
Rust, real EVM, cloud, browser and independent review qualifications remain
separate and unchanged.
