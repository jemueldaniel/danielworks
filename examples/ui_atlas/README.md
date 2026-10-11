# Atlas — five original interactive frontend patterns

A public-only, self-contained **frontend engineering reference** combining
commerce, workflow, messaging, editorial launch/onboarding and design-system
interfaces in one consistent, responsive UI. Every product, task, message,
price and plan is synthetic. The source was authored independently of any
private company application; it does not import logos, screenshots, local
files, credentials, customer data or startup product designs.

## Run the actual interface

From examples/ui_atlas, start a localhost-only static file server:

    python -B -m http.server 4322 --bind 127.0.0.1

Open http://127.0.0.1:4322/ in a modern browser. The port is illustrative:
choose an unused port when needed. Do not expose a development static server
on a public network. Local ES module imports usually require an HTTP origin,
not a file:// URL.

## Repeatable acceptance

From the repository root:

    node --test --test-reporter=tap examples/ui_atlas/test_model.mjs
    npm ci --offline --ignore-scripts --no-audit --no-fund
    npm run test:atlas

The Node state tests use no third-party packages; this is what the
**source-pinned one-command public starter** exports and executes. Browser
tests require a supported, already-installed Chromium/Microsoft Edge and
pre-cached npm dependencies. Set BROWSER_PATH if the installed executable
has a nonstandard location. The browser suite runs only against a temporary
127.0.0.1 static server, with a fixed URL/file allowlist and no fetches,
model calls, telemetry or third-party assets.

## What works beyond static mockups

- **Commerce:** search/category filters, six original CSS product visuals,
  increment/decrement/remove cart actions, verified fictional totals and
  a deliberately simulated (nonpaying) checkout
- **Kanban workflow:** three status columns, task-creation dialog, task
  priority, keyboard-operable native status selectors and live counts
- **Messaging:** three synthetic conversations, thread switching, compose
  and send, accessible log and literal untrusted text rendering
- **Marketing and onboarding:** responsive editorial hero, pricing interval
  selector, plan chooser and validated three-step reversible local wizard
- **Design-system components:** responsive text and color tokens, theme,
  buttons, statuses, accessible forms, reusable original token JSON export
- **Cross-cutting:** semantic landmarks, skip-to-content navigation, named
  controls, focus-visible outlines, Escape/focus restoration for dialogs,
  reduced-motion support, local theme persistence only, genuine downloads,
  strict input bounds and browser acceptance from 320 through 1440 pixels

## Boundaries

These are independently authored **educational UI references**, not
production commerce, financial checkout, chat services, user accounts,
multi-user Kanban, email capture, server state or client-specific designs.
Their controls intentionally make no external mutations. A passed
headless browser suite does not establish complete accessibility,
independent UX usability results, production-level security or permission
to reuse unrelated employer implementations. A full accessibility review
requires manual screen-reader testing and cross-platform assistive-tech
verification.

To adapt for work, pin the published source manifest externally, run
tests against approved fixtures, review licensing and source rights, and
build real identity, backend, authorization, validation, rate controls,
persisted storage, monitoring, asset governance and deployment approval
separately. Keep all private code and proprietary brand designs out.
