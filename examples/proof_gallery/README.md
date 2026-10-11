# DanielWorks — original public Engineering Proof Gallery

An independently implemented, responsive interview-focused evidence explorer. It
links curated **already-public** example implementations and tests in DanielWorks
without importing private client/company software, confidential screenshots,
startup names, personal data, credentials, local workspace paths or telemetry.

It is a real, functioning frontend:
- searchable and sortable catalog of 19 original PUBLIC demonstrations;
- discipline and evidence-level filters, including explicit historical labels;
- case-study dialogs with implementation/test links and Escape/focus behavior;
- keyboard command palette; saved references, light/dark local-only preferences;
- compare up to three generic public implementations;
- public-only JSON and formula-safe CSV evidence downloads;
- fixed one-shot recipe command selection with an **external** source hash placeholder;
- mobile/desktop responsive layout and reduced-motion support.

## Run locally

From the repository root:

    python -B -m http.server 4331 --bind 127.0.0.1

Open http://127.0.0.1:4331/examples/proof_gallery/ (choose an unused port).
The demo uses no runtime dependencies, accounts, external CSS/fonts/scripts, or
external network requests. GitHub source links open only when explicitly chosen
by the user. Do not expose the Python demo server to a public interface.

## Test

    node --test --test-reporter=tap examples/proof_gallery/test_model.mjs
    npm ci --offline --ignore-scripts --no-audit --no-fund
    npm run test:gallery

The browser suite serves only five allowlisted files over real 127.0.0.1 HTTP,
uses an already-installed Edge/Chromium and checks actual DOM interactions,
downloads, focus, keyboard behavior, storage, invalid text and viewport overflow.
It never installs a browser or calls third-party services. For a differently
located installed browser set BROWSER_PATH.

## Reuse and qualification boundaries

The corresponding **proof-gallery** starter exports this module and executes
its deterministic public model tests from a source-pinned checkout. The
**career-portfolio** recipe composes the gallery with four independently
authored interface demonstrations. Browser tests are included in the full
repository, not the standalone six-file starter.

Public examples have exactly the qualification documented in
docs/PUBLIC_CAPABILITIES.json. A local pass is not equivalent to production
deployment, legal ownership, a professional license, complete accessibility
certification or independent security assurance. Historical cases remain
historical in the interface. Never infer that private code may be copied into
this project. Publication only includes new original source authored separately
from private projects, and strictly public documentation links.

The gallery does not read private GitHub repositories or local directories at
runtime; its evidence registry is a fixed, manually reviewed list of public
GitHub paths. Only explicitly saved identifiers and theme are stored locally.
