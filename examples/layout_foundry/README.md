# Layout Foundry — an original, runnable UI reference

Layout Foundry is a self-contained, privacy-safe frontend built from original HTML,
CSS and JavaScript modules. All eight initial work items are fictional. Nothing
is imported from any client, employer or private company repository.

## Open the real interactive application

From this directory:

    python -B -m http.server 4341 --bind 127.0.0.1

Open http://127.0.0.1:4341. Use a free local port if 4341 is occupied.
Never expose the development server to a public network.

## Run the exact tests

From the repository root:

    node --test --test-reporter=tap examples/layout_foundry/test_model.mjs
    npm ci --offline --ignore-scripts --no-audit --no-fund
    node --test --test-concurrency=1 projects/layout-foundry-tests/browser.test.mjs

The model requires Node.js only. The browser tests require the preinstalled
Microsoft Edge/Chromium executable and Playwright from the pinned public lockfile;
no browser install is authorized by the tests. Browser traffic is constrained to a
127.0.0.1 allowlisted static test server with no third-party requests.

## Usable features

- Responsive editorial shell, multi-density dark/light design system, visible
  focus, reduced-motion support and skip navigation.
- Fictional work table with search, filtering, sorting, workflow transitions,
  progress summary, local state persistence and explicit sample reset.
- Native dialog with focus restoration, validation and 120-item local cap.
- Ctrl/Command+K searchable command palette and keyboard navigation.
- Bounded interactive hue, radius and density tokens; actual local CSS/JSON
  exports; safe CSV export with spreadsheet formula neutralization.
- No services, telemetry, external fonts, remote images, analytics or wallets.

## Evidence boundaries

Automated behavior and browser acceptance can show that this original sample
works under the tested conditions. They cannot establish independent UI usability
research, WCAG certification, security certification, personal ownership of
private commercial work, or production-level backend, identity and deployment
capabilities. Local storage is a demo convenience and is not a secure database.

This module is intentionally separate from the existing reusable exporter and
any parallel uncommitted Operations Desk work. Integration into new fixed-profile
recipes requires a separately reviewed, source-pinned acceptance release.
