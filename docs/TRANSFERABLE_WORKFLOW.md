# Transferable engineering workflow: proof before claims

This public document is employer-neutral. It includes no confidential customer,
organization, startup, or local-account names or artifacts. The accompanying
`tools/export_public_starter.py` is an **executable source-pinned reference
exporter**, not an automated replacement for engineering assessment.

## A reusable one-project-at-a-time sequence

| Gate | Concrete action | Evidence to retain | What it does **not** establish |
|---|---|---|---|
| 1. Contract | Write user journeys, failure states, data lifecycle, budgets and threat model | Versioned acceptance checklist | Implementation completion |
| 2. Source | Select only permitted public code and pin its revision externally | Hash-bound inventory | Ownership or license suitability |
| 3. Design | Separate UI/API, permissions, persistence, asynchronous effects and transport | Interface and rollback contracts | Authentication or deployment |
| 4. Prototype | Run a bounded public example in isolation | Exact commands and observed outputs | Product architecture equivalence |
| 5. Failure | Test input limits, replay, cancellation, corrupt state, cross-tenant isolation and recovery | Red/green regression log | Security certification |
| 6. Integration | Run tests on target operating systems, real browsers, database and network protocol | Per-platform test receipts | All environments or future reliability |
| 7. Review | Obtain an independent privacy, attribution, correctness and threat-model review | Hash-bound verdicts | Formal audit unless performed |
| 8. Delivery | Build from clean pinned commit with explicit release effects and reversible rollout | Remote file readback and restore proof | Deployed service without live checks |

## Starter profiles and evidence boundaries

The exported profiles intentionally stay small enough to reproduce without
credentials or nonpublic services. Each profile copies its public source,
README, fixtures and tests into a new folder. It does not silently change the
qualification category in `docs/PUBLIC_CAPABILITIES.json`.

- **Agent:** checkpoint identity, permission changes, cancellation, recovery;
  in-process only, not distributed effects.
- **Jobs:** SQLite persistence and lease/recovery; not a cloud queue.
- **Event inbox:** signed bounded HTTP ingestion, idempotency, fenced SQLite leases and restart tests; not an external SaaS or exactly-once delivery.
- **Training:** generated-data CPU optimizer and resume tests; not GPU/LLM training.
- **Retrieval/evaluation:** synthetic ranking and inspectable misses; not
  proprietary search quality.
- **Typed API reference:** historically qualified public SDK slice, explicitly
  opt-in; no employer service integration.
- **Rust compiler reference:** historically qualified lexer/IR/VM slice,
  explicitly opt-in; not a production sandbox.

## Safety contract

The generator never reads private repositories or produces private-proof JSON.
It rejects destination overwrites, source-file drift, missing external hashes,
unverified/historical profiles without explicit selection, symlink-backed source
and excessive output size. A successful export proves byte-consistent copying,
**not** that the generated examples have already been tested in the destination.

To reuse a concept at a future job, obtain approval to use and transform any
existing code, then implement from the public example under the employer's
licenses, controls and review process. Private implementation evidence can be
reviewed privately without ever being republished as a source tree.

## Independent verification after export

The exporter reports `output_manifest_sha256`. Preserve it **outside** the exported directory, then run:

```sh
python -B tools/verify_exported_starter.py --destination /tmp/public-example --expected-manifest-sha256 OUTPUT_MANIFEST_SHA256 --run-tests
```

This new tool checks source-file hashes, included README integrity, file inventory, path and size safety, and the mandatory externally supplied output digest *before* launching any test. Runtime commands are fixed to known, public example profiles, rather than read from editable manifest text. It reports a test failure if a selected runtime is missing, a command exits unsuccessfully, or zero tests actually ran. Tests for a historically qualified profile remain **historical evidence** even after the public example's own tests pass locally. No customer, employer, private repository or connected service is accessed by the verifier. This is not a full production application or a generic secure code-execution sandbox.

## One-shot project assembly with independent acceptance

Use `tools/one_shot_public_project.py` to compose only the existing permitted public examples. Pass the externally confirmed `SOURCE_MANIFEST.json` SHA-256 and choose profiles with `--profile` (repeatable) or `--all-executed` (currently seven executed sample profiles). The pipeline invokes the original source-pinned exporter, validates the generated kit against its **externally returned output-manifest SHA-256**, runs only fixed per-profile tests, then validates the kit *again*. It refuses missing tests, test failure, changed files, duplicate selections, unsafe destinations and overwrites.

```sh
python -B tools/one_shot_public_project.py \
  --root . \
  --expected-source-sha256 YOUR_OUT_OF_BAND_SOURCE_MANIFEST_HASH \
  --destination ../fresh-reference-system \
  --all-executed \
  --receipt ../fresh-reference-proof.json
```

Child test processes receive a minimal set of OS and runtime variables; unrelated ambient secrets and injection options are not forwarded. The pipeline does not isolate hostile code. The receipt is placed outside both the source tree and exported kit and is written **exclusively** (never overwritten). It contains source and output hashes, selected profiles, actual tested groups and retained historical qualification labels—not private paths or logs. `--no-tests` reports only `PASS_VERIFIED_ONLY`. If testing fails, the generated directory remains for inspection with a `FAIL` result and **no successful acceptance receipt**. A receipt cannot certify employer rights, code authorship, SaaS operation, security review, deployed transactions, production-scale training or trusted execution of unknown code. Every actual employer integration requires separate requirements, licensing approval, security controls and target-runtime acceptance.

The complete workflow is covered by `tools/test_one_shot_public_project.py`, including an end-to-end six-profile export and test run, tamper checks before/after execution, no-overwrite and historical opt-in cases. These are not credentials, connectors or external deployment steps.

## New public-only full-stack profile

`--profile proof-platform` exports the independent [Portable Proof Studio](../projects/portable-proof-studio/README.md). A clean Python standard-library runtime exercises 36 distinct HTTP/SQLite/workflow/evaluation/static-web tests with an actual local database and restart validation. It does not copy product repositories, deploy a worker, call a provider or make this test fixture production-authenticated.

```sh
python -B tools/one_shot_public_project.py \
  --root . --expected-source-sha256 YOUR_EXTERNALLY_VERIFIED_MANIFEST_SHA256 \
  --destination ../fresh-proof-platform --profile proof-platform \
  --receipt ../fresh-proof-platform-receipt.json
```

Reproducibility, isolation and hash checks are local acceptance; native browser navigation is separately blocked by environment policy and must not be called passed.


## Signed event ingestion and durable delivery profile

The original `--profile event-outbox` module contains a local,
authenticated event ingestion adapter and a SQLite inbox/outbox with worker
lease fencing. It is directly reusable as a **design exercise** for webhook
verification, durable processing and recovery, while still needing employer
architecture review and rights clearance before adaptation. Its generated
source includes all signing, lease, HTTP and recovery tests, not a static
mockup.

```sh
python -B tools/one_shot_public_project.py   --root . --expected-source-sha256 YOUR_EXACT_EXTERNAL_SHA256   --destination ../event-reference --profile event-outbox   --receipt ../event-reference-proof.json
```

Its local HMAC key is a synthetic fixture, not a real integration credential.
A consumer performing remote effects must independently deduplicate those
effects. No company service, live deployment or provider authorization
is assumed.

## Authorization and audit-evidence reference (new)

The original tenant-policy profile demonstrates strict tenant isolation,
versioned allow/deny policy rules, ownership restrictions and canonical,
short-lived HMAC audit receipts. Recompute policy for every protected action;
never treat audit evidence as an access token. Integration requires trusted
authentication, real tenant membership and resource ownership sources,
signing-key management, revocation, observable failures and security review.

To include it in a new, SHA-256-pinned *public-only* reference project,
select the policy profile with the existing one-shot assembler. Use the
external manifest SHA-256 belonging to the exact published revision. Do not
copy private company logic, keys or deployment configuration into a new job.

## From original public examples to a one-command new reference project

Use the recipe composer documented in PUBLIC_RECIPES.md. Provide the SHA-256
of the exact published public source manifest out of band, select a predefined
recipe, and choose unused destination and receipt paths. The composer calls
the existing source-pinned assembler, runs fixed tests in a restricted child
environment, and verifies every output byte again after testing.

These are sample building blocks, not a production system or a license to
transfer proprietary employer/customer code. Adapt ideas independently and
qualify identities, keys, cloud configurations and real service behavior.

## Independent indexed retrieval building block

The hybrid-search public profile can be included in the one-shot
source-pinned exporter and ai-search recipe. Its SQLite FTS5 BM25
and deterministic hashed token vector are local lexical ranking tools;
do not describe them as pretrained semantic embeddings. The test
suite includes a deliberately negative retrieval case, tenant boundaries
and corrupted-index detection. At a new employer, substitute separately
authorized datasets and services, add trustworthy identity, and run fresh
relevance benchmarks before making production claims.

## Preserve reliable evidence about intermittent test failures

Use the new repeatability diagnostic for externally pinned public starter exports. It accepts the **export manifest** hash and the existing profile allowlist, not arbitrary commands or private repositories. Run two or three explicit rounds when investigating nondeterministic tests and preserve every negative result. A later pass never erases an earlier failure. See REPEATABILITY_DIAGNOSTICS.md for the command and qualification boundaries. This does not fix the underlying operating-system or socket behavior.

## Adapt schema migration skills safely

The approved public migration profile is part of service-foundation and
full-reference. Review migration SQL before execution, pin the source
manifest externally, and test a fresh SQLite instance. Production use
must add backups, real database access controls, monitoring, compatibility
and rollback/restore drills. Do not transfer employer or startup schema.

## A reusable DAG planning baseline

Select the build-graph profile or the workflow-engine recipe from the
source-pinned assembler. Demonstrate a cycle rejection, content hash
invalidation, concurrent worker claims, stale-lease rejection and
a verifiable unkeyed receipt. Use independent source with explicit
permissions; never reuse private employer or startup files.
Production additions need durable shared lease storage, identity
validation, resource accounting, secure sandboxing, cross-node fencing
and failover trials. In-memory examples are not production agents.

## Assemble a local API security teaching reference

The signed-api profile and api-security recipe are part of the
source-pinned public-only assembler. The sample uses fictional credentials,
binds its server to 127.0.0.1, and exercises actual HTTP request signing,
tenant scope, persistent nonce fencing, timestamp windows and quotas.
For legitimate employer use, replace synthetic keys with approved managed
secrets, use TLS and IAM, add real identity and resource authorization,
review audit logs and run negative cloud/load tests. No proprietary
service logic, startup credentials or private interfaces are inputs.

## Reuse a real frontend without private product assets

Select interface-lab for a self-contained HTML/CSS/ESM UI sample, or
frontend-studio to package the UI alongside separate, independently tested
jobs and policy examples. Run the source-pinned one-command exporter first,
then execute its fixed, dependency-free Node state tests. For end-to-end UI,
serve the original public example from localhost and run the root
Playwright browser acceptance against an installed local browser.
Demo filtering, navigation, theme reload, CSV download, semantic dialogs,
keyboard shortcuts, mobile overflow and error handling. This does not
license private startup/client UI, unreleased brand assets or proprietary
design files for reuse.
