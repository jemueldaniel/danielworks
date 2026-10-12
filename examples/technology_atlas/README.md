# DanielWorks — original Technology Atlas

An independent, local-first personal technology and engineering evidence index,
designed to show breadth without presenting private code or making unsupported
production claims. The curated list contains **87 technology/method entries**:

- **52 Public-tested:** original public implementations, linked to an inspected
  repository file, with separately documented model, browser, API or Python
  test evidence in the corresponding module.
- **2 Public-historical:** public examples with retained earlier test records,
  but without a fresh test of that particular toolchain in this release.
- **33 Source-observed:** generic technology names supported by read-only
  inspection of private repository file types, configuration and/or dependency
  metadata. No private code, company names, internal URLs or repository paths
  are disclosed in the public atlas. Such observations do **not** prove
  production success, authorship or redistribution rights.

The atlas contains seven disciplines, search and qualification filters,
saved technologies, safe local JSON/CSV exports, accessible details,
keyboard command palette, responsive light/dark design and a bounded
selection review that never converts private observations into a public
passing claim. The one-shot command chooser only emits previously approved
source-pinned public recipe names with an explicit external hash placeholder.

## Run the actual interface

From repository root:

    python -B -m http.server 4332 --bind 127.0.0.1

Open http://127.0.0.1:4332/examples/technology_atlas/

The index imports only public files in this directory. No external CSS,
fonts, images, analytics, accounts, remote services or private-source reads
are made by its runtime. Source links open GitHub only if clicked.

## Independent tests

From root:

    node --test --test-reporter=tap examples/technology_atlas/test_model.mjs
    npm ci --offline --ignore-scripts --no-audit --no-fund
    npm run test:technology-atlas

The Node tests exercise classification bounds, source-file existence,
source-path allowlisting, evidence-level filtering, stable export, saved
preferences, selected stacks, CSV formula injection prevention, and fixed
recipe safety. The browser tests require **already installed** Edge/Chromium
and the repository-pinned Playwright dependency. They serve only allowlisted
static files over localhost HTTP, check five phone/desktop widths, real
interaction and download behavior, keyboard/focus flow, and no external
network access while actions execute.

## Reproducible public starter

The technology-atlas public profile copies only this original directory
into a nonoverwriting, source-pinned starter and runs its fixed Node tests.
The tech-and-interface public recipe combines technology-atlas with
proof-gallery, interface-lab, ui-atlas, flow-lab, and data-studio
as six separately executed original public models. Their browser suites run
from the full repository and are not misrepresented as part of an exported
standalone starter.

The external SHA-256 pin is mandatory. The sample command intentionally
shows YOUR_EXTERNALLY_VERIFIED_MANIFEST_SHA256 rather than using an
unverified or stale hash.

## Explicit exclusions

The dataset is a bounded review of accessible GitHub repository trees and
two Windows Git-index snapshots. It is **not** an exhaustive accounting of
everything created, nor a proof that every mentioned tool was personally
authored or mastered. Presence of Solidity files does not prove an on-chain
transaction. A React dependency does not prove shipping a product. A Docker
configuration does not prove managed cloud operations.

Not demonstrated by this index: production system security, contractual IP
ownership, a professional certification, hosted availability, verified
production PostgreSQL RLS, distributed model training, independent accessibility
audit, blockchain settlement, or complete codebase provenance.

The private repositories are not inputs to the runtime or public
one-command assembler, and they remain unchanged.
