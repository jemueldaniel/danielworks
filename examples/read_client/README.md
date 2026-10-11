# Bounded TypeScript read client

## Problem and implementation

A retry loop is not reliable when it waits indefinitely for a response body, follows a redirect, retries an authorization failure, or clears its timeout before asynchronous validation finishes. This example implements a small typed **GET-only JSON client** with one overall deadline, caller cancellation, bounded transient retries, response-byte limits and runtime decoding.

The implementation, JavaScript behavioral tests and compile-only TypeScript assertions are newly written with AI assistance. It is not a vendor SDK, MCP server, WebMCP adapter or authentication system.

## Architecture

`validated options and URL → GET → classify response → bounded body read → runtime decoder → typed result`.

The same abort signal and monotonic deadline cover transport, backoff, body reading and asynchronous validation. The client races asynchronous work against cancellation, checks elapsed time while draining streams to avoid timer starvation, and discards late responses or failed response bodies. A decoder can return either data or a promise for data. Transport and decoder dependencies are trusted application code; synchronous infinite loops cannot be preempted here.

## Run and test

Prerequisites: Python 3.11+, Node.js 22+, and an already installed TypeScript compiler 5.8+. No package installation command or package lifecycle hook is invoked. From the repository root:

```sh
python tools/verify.py --component sdk
python tools/verify.py --demo sdk
```

The runner invokes `tsc --project examples/read_client/tsconfig.json --outDir <temporary-directory>`, then runs Node's built-in tests against that exact compiled module. The temporary directory is removed. `types.test.mts` contains compile-only inference and invalid-call assertions; it is never executed. No compiled source maps or bundles are committed.

The demo injects a synthetic transport: first a 503 response, then `{"count":7}`. Its actual computed output is:

```json
{"transport":"synthetic","attempts":2,"result":{"count":7}}
```

The behavioral suite mainly uses synthetic `Response` objects. One integration test starts an actual HTTP server on an ephemeral **127.0.0.1** port, verifies a 503-to-200 GET retry, verifies a redirect is not followed, and closes the server and its connections. It makes no request to an external service. The demo itself makes no network request.

## Policy and tradeoffs

The client supports **GET only**. It retries transport `TypeError` failures and HTTP 429/502/503/504, with 1–5 total attempts and exponential delay capped at one second. It assumes the chosen server honors GET's read-only contract; it cannot prove a remote server is side-effect-free. Partial-body failures, malformed JSON, invalid UTF-8, decoder failures, redirects and other HTTP errors are terminal.

`Retry-After` delta-seconds are honored when they fit the remaining deadline. Long waits, unsupported HTTP-date forms and malformed values return `retry_later` rather than retrying too early. Jitter and HTTP-date support are intentionally not implemented. The caller decides whether to schedule a later, separately authorized request.

The deadline is 1–30,000 milliseconds; the default is 1,000. A successful body is capped at 1–65,536 bytes; the default is 16,384. Content-Length can reject an oversized response early, but the streaming cap is enforced independently. Empty chunks are not retained. JSON media types are checked. Error messages use stable codes and do not echo server bodies or exception text.

Cookies are omitted and redirects are manual/terminal. HTTPS is required except for an explicit test allowance for literal loopback HTTP. Embedded URL credentials and fragments are rejected. No authorization header, credential store, model API or mutation method is present.

## Known limits

This is not an SSRF filter: supply an application-approved URL, not an untrusted server-side user URL. It does not implement DNS/IP allowlisting, caching, authentication, pagination, connection pooling, rate-limit coordination or service discovery. Standard JSON parsing uses last-value behavior for duplicate object keys; an application with a stricter trust contract needs an appropriate parser and decoder.

Cancellation settles this client's promise, but cannot force an uncooperative transport or decoder to stop its own work. The byte limit bounds accepted payload data, not total network-stack memory. Synchronous dependency code cannot be forcibly interrupted. Browser compatibility, CORS behavior, screen-reader/accessibility behavior and live third-party endpoints have not been qualified. Passing these tests does not establish production readiness or security-audit completion.
