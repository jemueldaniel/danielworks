# Portable Proof Studio — original local full-stack evidence

A complete *local* four-step Workflow → Knowledge reference implemented from scratch, without any private company source or cloud dependency. Recruiters can start an isolated test workspace, save a fixed-graph text workflow, execute it, inspect actual step output and persisted artifact, explicitly import that artifact into a document collection, search and run a deterministic top-1 evaluation. HTTP calls operate on a real SQLite database; results survive process restart. The interface is responsive and keyboard-addressable; automated native browser navigation **has not been qualified** in the current environment.

## Run without installing packages

Requires Python **3.11+** with built-in SQLite. Run from the repository root:

```sh
python -B projects/portable-proof-studio/server.py --db ./portable-proof-demo.sqlite --port 8078
```

Open `http://127.0.0.1:8078/` on the **same computer**. It binds only to loopback. Use the "Start a test workspace" button, save a workflow, run text, import the artifact into the Knowledge Lab, search for an artifact keyword and evaluate against the expected saved document. Refresh and repeat to confirm server-side readback. The opaque test-workspace token is kept in the browser tab's `sessionStorage`; the database stores only its SHA-256 digest. Never enter real personal, company or sensitive information.

## Independently execute the tests

```sh
python -B -m unittest discover -s projects/portable-proof-studio -p 'test_*.py' -v
```

The suite covers genuine local HTTP and SQLite operations, process-restart readback, workflow revisions, idempotency-key replay/conflict, concurrent duplicate submissions, document identity changes, active-index deletion, cross-workspace denial, excerpt/source hashes, search and evaluation failures, host/origin restrictions, duplicate JSON keys, static interface constraints and bounded inputs. Each test uses its own temporary database.

## API contract

| Method | Local endpoint | Result |
| --- | --- | --- |
| POST | `/api/workspaces` | Issue an expiring *demo* workspace token; `{}` body |
| GET / POST | `/api/workflows` | Read or save a fixed four-step workflow |
| POST | `/api/workflows/update` | Version-fenced edits to supported step configuration |
| POST | `/api/runs` | Synchronous execution with run, trace and saved artifact identity |
| GET | `/api/runs/{id}` | Read back an actual saved run, never start it |
| GET / POST | `/api/documents` | List or save workspace-scoped text documents, including explicit artifact imports |
| POST | `/api/documents/update` | Version-fenced document update and reindex |
| POST | `/api/documents/delete` | Remove active document data; **not backup erasure** |
| POST | `/api/search` | ASCII lexical token counts, stable ordering, source excerpt and corpus fingerprint |
| GET / POST | `/api/evaluations` | List or persist one expected-document top-1 evaluation |

All workspace routes take `X-Demo-Workspace`. Mutations take a client-generated `Idempotency-Key` (8–64 safe characters). Matching requests return one committed response; a changed intent conflicts with 409. Workspace token validation occurs before replay; mutations run within SQLite `BEGIN IMMEDIATE` transactions. No unrestricted graph execution, shell, SQL, browser agent or external tool capability is available.

## Trust, security and feature boundaries

- **Local-only by design.** This is **not** a production authentication service, hosted deployment, shared multi-tenant platform, CSP audit or secure untrusted-code sandbox. Test workspace tokens are guest bearer capabilities, not real verified users.
- Workflow execution is **synchronous and deterministic** with exactly four supported steps. It does not implement arbitrary visual DAG editing, background queue cancellation, distributed transactions or multi-node replay.
- Lexical retrieval uses ASCII token matches; its scores are occurrences, **not** relevance probabilities or semantic embeddings. The one-case evaluation returns a recorded correct/total metric, not model-quality certification. Changed/deleted documents change active corpus identity; old evaluation receipts remain version fingerprints, not reproducible snapshots of deleted data.
- The UI uses only locally served scripts, DOM `textContent`, strict same-origin HTTP, a browser-tab workspace token, keyboard-accessible forms, visible focus and reduced-motion CSS. **Automated real Chromium navigation was blocked by the current execution environment**, so end-to-end browser/device accessibility remains unverified. HTTP and static DOM contract tests are not equivalent to browser acceptance.
- Inputs are bounded; the service has workspace/document/run/operation quotas and an absolute token expiry. Cleanup of historical SQLite WAL, backups, or local database artifacts is **not demonstrated**. The caller owns deletion of the demonstration database.
- No connected GitHub, Drive, startup source, company brand, private data, wallet, payment, production cloud Worker/D1, PostgreSQL, model provider, EVM or remote API is read or invoked.

## Reuse

With an externally verified repository source-manifest hash, select the `proof-platform` profile in `tools/one_shot_public_project.py` to export these nine files into a new local directory, verify every byte, run the contained tests and save an external receipt. Its built-in modules are original public examples, not a legal opinion about merging them into employers' products. Review and qualify separately for the intended deployment.
