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

Use `tools/one_shot_public_project.py` to compose only the existing permitted public examples. Pass the externally confirmed `SOURCE_MANIFEST.json` SHA-256 and choose profiles with `--profile` (repeatable) or `--all-executed` (currently five executed sample profiles). The pipeline invokes the original source-pinned exporter, validates the generated kit against its **externally returned output-manifest SHA-256**, runs only fixed per-profile tests, then validates the kit *again*. It refuses missing tests, test failure, changed files, duplicate selections, unsafe destinations and overwrites.

```sh
python -B tools/one_shot_public_project.py \
  --root . \
  --expected-source-sha256 YOUR_OUT_OF_BAND_SOURCE_MANIFEST_HASH \
  --destination ../fresh-reference-system \
  --all-executed \
  --receipt ../fresh-reference-proof.json
```

Child test processes receive a minimal set of OS and runtime variables; unrelated ambient secrets and injection options are not forwarded. The pipeline does not isolate hostile code. The receipt is placed outside both the source tree and exported kit and is written **exclusively** (never overwritten). It contains source and output hashes, selected profiles, actual tested groups and retained historical qualification labels—not private paths or logs. `--no-tests` reports only `PASS_VERIFIED_ONLY`. If testing fails, the generated directory remains for inspection with a `FAIL` result and **no successful acceptance receipt**. A receipt cannot certify employer rights, code authorship, SaaS operation, security review, deployed transactions, production-scale training or trusted execution of unknown code. Every actual employer integration requires separate requirements, licensing approval, security controls and target-runtime acceptance.

The complete workflow is covered by `tools/test_one_shot_public_project.py`, including an end-to-end five-profile export and test run, tamper checks before/after execution, no-overwrite and historical opt-in cases. These are not credentials, connectors or external deployment steps.
