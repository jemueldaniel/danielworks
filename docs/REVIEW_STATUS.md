# Review record and scope

## Completed: Rust exact-source independent static review

A separate read-only reviewer verified the hashes of the eight files under `projects/bounded-lang` and returned: **acceptable with two low-severity, non-blocking observations; no unresolved blocking defect in the reviewed files**. The coordinator verified that the files were unchanged after review. This was not the implementing coordinator's self-review. The reviewer did not run tests, install dependencies, use GitHub, inspect company source or modify files.

The reviewed `src/lib.rs` SHA-256 is `04bab003edc418304b38081b38189c92a4f3b253920a04c083be2e99c988d959`. It implements separate total-binding allocation, prior-environment initializer resolution, checked local counts, source/token budgets and rejection of empty public IR blocks. The current source manifest identifies the other seven files.

### Disposition of observations

The VM checks operand-stack length after each instruction. A failing `Push` or `Load` may temporarily allocate one extra operand before returning `StackLimit`; no next instruction executes with that state. This is accepted as a **documented bounded-execution limitation**, not a strict allocation or OS-memory ceiling. The project README already states the absence of an OS sandbox or allocation guarantee. A future strict pre-allocation limit would require its own testable API contract.

Compile-budget rejection tests assert rejection rather than the exact `CompileLimit` variant. The implementation currently returns the documented variant. These tests were first observed failing on the old implementation; they were not weakened to pass. This is accepted as a **low-severity test-specificity gap**, explicitly tracked in the single coverage matrix. Unknown names and arithmetic/runtime-limit variants have separate exact assertions.

The reviewer also identified intentional public-IR limitations: zero-initialized locals, incomplete verification of manually constructed programs, and ignored unreachable trailing instructions after return. The README makes no full-bytecode-verifier claim.

### Earlier findings resolved

An earlier independent inspection identified unbounded recursive compilation and free traversal of empty IR blocks. Four new regressions failed before correction. The source-size/token prepass and empty-block rejection were added; all 18 Rust tests, formatting and clippy subsequently passed. The final separate review confirmed the fixes in the exact source.

## Whole-candidate review

**Blocked: the available reviewer service reached its usage limit.** Two separate read-only review attempts were admitted for the foundations (28 files) and workbench (28 files). Both returned the service usage-limit error before source inspection, with no review report; both file sets remained unchanged. Neither worker is active. No credits were purchased, subscription changed, denied action retried or second identity used to bypass the limit.

Their compact sorted path→SHA-256 manifest bindings were `d6c4e081bcdd8e689146462fffbe2c58026cc2217e7b31c2cd69be0f191ac612` and `aa8e1c86666e6d9584563e7568d417fb28eb4411848876da997a12c9bf88ac13`. These are attempted-review input bindings, **not approval hashes**. Available independent-review capacity is still needed; the coordinator's self-review is not a replacement.

**Final integrated review is incomplete.** The Rust verdict alone does not approve the remaining showcase, dependency ownership, full privacy surface, repository settings or publication. Existing historical review packs include self-review and are not silently relabelled as independent approval. The publication gate remains closed until applicable exact-file review and trigger checks are complete.

Raw reviewer output contains local diagnostic paths and is retained privately. This document is a sanitized coordinator-written disposition, not a fabricated reviewer transcript or a security certificate.

The [sanitized actual Rust reviewer report](../verification/current/rust-final-independent-review.md) is included separately. Machine-specific link prefixes and line-link syntax were normalized; its review prose is unchanged.


## Later exact-file attempts — 7 October 2026

After the formerly stated service-reset time, six disjoint read-only reviewer processes were started: foundations (28 files), backend (six), frontend/integration (12), protocol (eight), source checker (two), and retained packaging/evidence (16). Every process exited with a service usage-limit error and produced zero report bytes. All input hashes were unchanged. None performed an approving review and none remains active. Current root documentation was outside the historical packaging scope; it is not silently claimed reviewed.

Their input bindings and dispositions are retained in `verification/checkpoint-2.json`. Available independent review capacity is still needed. No credits were purchased, identity switched, settings altered, or quota denial bypassed. The existing Rust review's eight hashes were separately reverified and are unchanged. The newly observed Windows HTTP failure also requires reviewed diagnosis; the earlier all-green result does not clear it.
