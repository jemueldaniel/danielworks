# Interfaces and execution contract

## HTTP

The gateway exposes `/api/{profile}/…`; the Python backend exposes `/v1/…`. Profiles are `reader`, `operator`, and `other-reader`. They select demo permissions and one of two synthetic tenant partitions. A caller cannot choose a tenant in the JSON payload. This is deliberately **not authentication**: selecting the operator route is public to local callers.

| Method and suffix | Input | Output / behavior |
|---|---|---|
| GET `dataset` | none | version, SHA-256, synthetic flag, document/query counts and engines |
| GET `search?q=password&k=2` | text 1–500 characters; k 1–3 | real FTS5 matches, deterministic score/id order |
| GET `jobs?limit=10&cursor=key` | limit 1–20; optional keyset cursor | bounded items and next cursor |
| GET `jobs/{key}` | lowercase ASCII key, 1–64 characters | persisted state/checkpoints/result, or 404 |
| POST `jobs` | exactly `{key,engine,k}`; engine `fts5` or `lexical` | idempotent submission; changed payload for key → 409 |
| POST `work` | `{max_cases:5}` | at most one claimed job and five new cases |
| POST `jobs/{key}/cancel` | `{}` | explicit durable cancellation result |

Writes require the operator profile. Unknown fields, malformed JSON, duplicate JSON keys at the Python boundary, nonfinite numbers, invalid cutoffs and oversized bodies are rejected. Errors use fixed public codes. A 5xx, timeout or failed confirmation is not evidence that a write did not happen.

For early rejected POSTs (403, 413 or 415), the Python backend writes the error response then consumes a fully declared payload of **at most 8,193 bytes** before closing the socket. The request must have exactly one valid `Content-Length` and no `Transfer-Encoding`. This does not retry effects or read a body that was already consumed; ambiguous/oversized bodies are closed without a potentially unbounded drain. It reduces the possibility of a connection abort on close with small unread payloads, but it does not guarantee delivery after network failure or prove that the historical intermittent Windows WinError 10053 is eliminated. The tests include direct no-network body-accounting cases and actual loopback status checks.

## MCP tools

`dataset_info`, `runs_list`, `run_inspect` and `search_preview` appear in read catalogs. The operator additionally receives `run_submit`, `run_cancel` and `work_once`. Input and output schemas are registered using Zod. Tool annotations describe behavior; actual registry/profile checks enforce the demonstration permission boundary.

The client performs `initialize` → `notifications/initialized` → `tools/list` / `tools/call`, carries a server-issued session ID, and uses DELETE on close. Sessions cannot move between profile routes. Missing initialization, unknown sessions, role misuse, extra fields, invalid media, request batches and foreign origins are tested separately. Batch JSON-RPC requests and standalone SSE are deliberately unsupported.

## Public TypeScript methods

`ApiClient`: `dataset`, `list`, `inspect`, `search`, `submit`, `cancel`, `workOnce`. GETs use the preserved bounded read client; writes are single-attempt. Each returned object is validated, and submission confirmation is identity-bound.

`WorkbenchMcpClient`: `connect`, the same named business methods, and `close`. Each method uses real official-SDK transport calls. Pre-aborted submission is not sent; post-dispatch ambiguity is conservatively reported. The wrapper does not expose an arbitrary tool name or caller-supplied tenant.

## Study sequence

Read a browser submission in `web/App.tsx`, then the single-attempt API method, gateway route check, Python request validator and original queue submission. Follow the checkpoint SQL fence and final call to the preserved grader. Finally read the lost-response and process-exit tests: the fault is injected around actual work, not used to replace the transport, storage or grader.
