# Demonstrable engineering skills — public-only proof playbook

Use this guide to present transferable engineering skills without exposing
private companies, source files, internal URLs, datasets, employee records,
credentials, business contracts or private architecture.

## Qualification levels

- **Executed public proof:** Run a fixed command from a pinned public source
  revision, show the actual pass/fail output, and explain the negative tests.
- **Source-verified only:** The bytes and declared source paths are pinned;
  this does not claim that the program executes successfully.
- **Historically observed:** Prior tests or inspections, not freshly rerun.
- **Not yet independently verified:** Production, licensing, personal
  authorship, or external services cannot be inferred from file counts.

## Reusable demonstrations

| Skill family | Independent public exercise | Positive / negative evidence |
|---|---|---|
| Compiler and VM | Bounded language parser/interpreter | Pipeline and overflow/step-budget cases; platform qualification retained |
| Agent systems | Bounded checkpoint execution | Crash/restart and rejection of invalid tool steps |
| Durable operations | SQLite job leases | Recovery and single-claim behavior, not distributed exactly-once |
| HTTP/MCP + full stack | Typed local API, browser workbench | Session permissions, recovery and mobile UI tests |
| Policy design | Deny-first tenant decisions | Cross-tenant rejection and deterministic audit receipts |
| Signed local HTTP APIs | Request-bound HMAC + SQLite | Replay, expired signature, quota and forged body rejection |
| Transaction arithmetic | Fictional-unit double-entry journal | Conservation and overdraw rejection |
| Schema evolution | Trusted-SQL migration gate | Idempotence, rollback and drift rejection |
| Retrieval quality | Lexical SQLite FTS5 ranking | Synthetic recall/MRR/nDCG and corruption detection |
| Workflow orchestration | Bounded DAG graph | Cycle rejection, incremental hashes, multi-worker fencing |
| CPU training and evaluation | Synthetic model exercises | Local repeatability, not distributed GPU proof |
| One-command reusability | Fixed-profile public recipe composer | Fail-closed source pins, non-overwriting receipts and post-test byte checks |

## A repeatable interview demonstration

1. Check out the exact published revision and independently verify the public
   SOURCE_MANIFEST.json hash. Record Python and Node versions.
2. Run one fixed profile's tests without accounts or private datasets.
3. Explain which invariant the successful run exercises.
4. Show one deliberate negative case (a cycle, stale lease, changed migration,
   cross-tenant request, invalid digest, or bounded response) and why it fails.
5. Generate a fresh recipe into an unused directory; run its tests and verify
   the byte-bound receipt. Preserve failed trials rather than only a green run.
6. State honestly what remains unqualified for production.

## Safe reuse inside a new company

Build and adapt the original public reference only after reviewing its
license and suitability. Authenticate real identities, design durable storage,
add service isolation, key management, database migrations, CI supply-chain
checks, observability, realistic performance tests and disaster recovery
before deployment. Never interpret access to historical private source as
permission to republish it. A metadata inventory alone cannot prove personal
authorship, acceptable third-party licenses or safe production deployment.

## Explicit unverified categories

Real funded blockchain interactions, security-audited contracts, live managed
PostgreSQL row-level security, cloud-scale transactions, multi-node GPU training,
production client deployment and independent full-package legal/security
review remain separately evidenced tasks. Synthetic demos are not substitutes.

## Reproducible UI/UX experience proof

From the public source reference, run the original UI on localhost and
exercise at least a phone-sized and desktop-sized viewport. Check keyboard
navigation, empty states, table sorting/pagination, creation validation,
Escape focus restoration, CSV download, reduced-motion CSS, theme reload,
and safe rendering of untrusted-looking text. A standalone model test does
not replace the installed-Edge acceptance. See UI_UX_EVIDENCE_MATRIX.md.

This demonstrates independently developed generic interface design, not
exclusive authorship, ownership or production suitability of any historically
private frontend or client work.
