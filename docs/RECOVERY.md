# Source recovery and preservation

## Second published checkpoint and Node test-report compatibility — 11 October 2026

The second public source checkpoint is [commit `f811ecf`](https://github.com/jemueldaniel/danielworks/commit/f811ecf09481ebe4d225620e1131753f1dd85b79), tree `e443a749e3810b9145bc65fdefb3b1a436554e3c`. All 109 files were read back from GitHub, and a new Windows clone with `core.autocrlf=false` verified both source files and committed Git objects against external manifest SHA-256 `61ec5ec1289112cabba561aa1604297b8a69115193bb9f215a7038e74a5be8b1`; the restored checkout was clean. Windows backend and offline Git-verifier test groups independently passed 28 and 9 tests, respectively. This is not a full locked npm/browser restore.

An additional correction to `tools/verify.py` and new `tools/test_verify_runner.py` fixes the original-example runner's false negative for Node 24's different default test-reporting format. The original Node 24 SDK test pass and wrapper failure are preserved as the red observation. The candidate requests stable TAP output, has six regression definitions and does not alter the earlier immutable Git commit or evidence. Future commit/tree and external source-manifest SHA-256 must be recorded outside the manifest after publication and readback, not embedded speculatively.

## Published source and independent checkout — 11 October 2026

The complete first public checkpoint is [commit `082086d4`](https://github.com/jemueldaniel/danielworks/commit/082086d4c64ed24db5a6ef8288b7517e3582668e), parented to the original initialization commit, with tree `8d0ca5fea7096b7cdccad2a7b39e1847cfcd66c9`. A 107-file GitHub source readback matched every expected SHA-256 and byte size, with no missing/extra paths or mode differences. In a new isolated Windows clone with `core.autocrlf=false`, all 107 files and the externally pinned manifest SHA-256 `282b77b1b10bae52845bc4b244dc364cd515043d09d3257573a263d271be65f3` matched; Git status was clean. These are publication/restore checks, not independent whole-package review or completed runtime qualification.

A new offline [`tools/verify_git_commit.py`](../tools/verify_git_commit.py) checks exact committed blob bytes separately from checkout bytes; its nine local-Git negative/corruption tests passed on Linux. Subsequent repairs require their own Git commit and receipt, rather than editing or claiming to have retested this immutable baseline. The earlier preservation and remote-state paragraphs below are retained historical observations, not assertions about today's `main`.

## Historical recovery lineage

Both expected candidate archives were verified from actual bytes in this cycle. The complete workbench archive was recovered in the container; the batch-2 archive was read and hashed on the authorized desktop. Its five original Rust files were recovered from that verified ZIP, not reconstructed from a report.

| Candidate | Observed bytes | SHA-256 | Inventory |
|---|---:|---|---|
| Complete workbench | 125,275 | `f5ba4d774813df98554c3c6bfe3f0d42fbe762bdfb4a7dbb6e01fe0aa50e86ac` | 78 files, all individually checked against the available source manifest |
| Batch-2 | 71,224 | `59f20bc1875b45e209971ec67ab1845029552eb1e27b47968d25e6d003ebbdb6` | 35 files; actual bytes supersede the older reported 71,778-byte size |

The initial union contained **83 distinct paths**: 78 workbench files plus five Rust additions. Thirty paths overlapped: 29 were byte-identical and only the root README differed. **All 48 workbench paths missing from batch-2 were recovered.** The comprehensive workbench README was retained and extended, not replaced with the shorter batch-2 document. Three new Rust regression files increase the core source set to 86 paths. New recovery/review/evidence documents and manifests are bookkeeping additions, not extra capabilities.

The 49-file transfer of the missing 48 paths plus comprehensive README was verified before writing. Its canonical UTF-8 JSON had 130,693 bytes and SHA-256 `d883bc9cf7a11a90f41e70d2b9c5114404cd1084a50239083c0aa5e0ef79ca47`. Each destination file was then compared with the decoded bytes. Two historical evidence files (`verification/backend-windows.txt` and `verification/versions.json`) had CRLF converted to LF in that text transfer; their original archive bytes remain preserved in this final candidate. No executable source, fixture or dependency lock changed as a result. No runtime source, dependency lock, fixture or original architecture file was guessed.

## Earlier deliveries and duplicates

The original 20-file candidate and expanded candidate were recovered and hashed. Their implementations, fixtures, examples and verifier survive in the full workbench. Six generated Python bytecode/cache files from the expanded archive were excluded. Original and expanded documentation remains available in the private recovery inventory; current public documentation merges their useful content rather than blindly duplicating stale variants.

The standalone root/project READMEs, browser test, backend, React App, protocol test, MCP client, server and test-evidence document were individually recovered. Each is byte-identical to its corresponding workbench file **before the explicitly recorded current documentation edits**; these are aliases, not extra public files. The supplied standalone checksum list was retained as a recovery artifact and compared with the available archives.

Original, expanded and workbench review packs were recovered. They contain earlier review and execution records, including self-review; none was automatically accepted as independent approval of this integrated candidate. Mixed/private audit artifacts, source inventories, raw machine-path transcripts and private provenance have no public destination. Their absence from public source does not block otherwise safe publication.

## Intentional changes after recovery

Rust `src/lib.rs` and its README were updated; three regression files were added. All six original Rust tests remain. In the original queue suite, only the rollback-test fixture's two SQLite connection lifetimes were corrected after an observed Windows cleanup failure; no test or assertion was removed and the queue implementation is unchanged. Root/coverage/provenance/evidence documentation was merged to record the complete scope and current status. All other recovered implementation, architecture, test, fixture and lock bytes remain preserved unless the manifest records a reviewed later correction.

The final source manifest lists every included path, size and SHA-256, and the recovery mapping distinguishes recovered, modified and newly authored files. Generated caches, `node_modules`, `dist`, Cargo targets, local databases, browser binaries, private audit archives and credentials are excluded. Identical standalone copies are not published twice; distinct code/test/lock files are not removed merely to make the count smaller.

## Historical repository reconciliation before publication

The then-last verified `main` was `3e69552cb5f9ae52639d30c2c865347fa3575ceb`, tree `e2fc8297de2120851ffd92f503dfd28639479dce`, containing the initial 13-byte README. No candidate commit or ref change is claimed. Three previously reported blob operations do not establish publication: their exact prior response identities were not recovered, and read-only checks of candidate-computed object IDs returned 404. No tree/commit/ref was created in this cycle. Latest remote state must be reconciled again before publication; no old parent is assumed safe indefinitely.

A newly generated Linux rerun summary matched `verification/original-60.json` byte-for-byte. The original path remains intact; the new duplicate was omitted. Final distinct-file inventory: **100 files including the manifest** (86 recovered/core paths and 14 current documentation/evidence/manifest additions). This count is not a capability-completion percentage.
