# Interface Laboratory — original, reproducible UI and UX source

An independently authored self-contained frontend reference with synthetic data.
No external font, CDN, API account, analytics library, model call or private
interface is needed for the static UI.

## Run the interface

From examples/interface_lab, start a localhost-only static server:

    python -B -m http.server 4311 --bind 127.0.0.1

Visit http://127.0.0.1:4311/ in a browser. Choose another free port if needed.
Do not load as file:// because ES module imports require an HTTP origin in
many browsers. Do not expose the development server on a public interface.

## Run acceptance

From the repository root:

    node --test --test-reporter=tap examples/interface_lab/test_model.mjs
    npm ci --offline --ignore-scripts --no-audit --no-fund
    npm run test:interface

Offline npm installation requires already cached packages. The actual browser
tests launch an already installed Edge or Chromium executable (configure the
BROWSER_PATH environment variable if necessary). No browser is downloaded.

The source-pinned public starter runs only the dependency-free state-model
tests. Browser tests live in projects/interface-lab-tests/browser.test.mjs,
separately qualified because the exported kit does not contain node_modules.

## Implemented interface capabilities

- Responsive UI at 1440, 1024, 768, 390 and 320 pixel desktop/tablet/mobile
  widths, with browser assertions against horizontal page overflow
- Semantic landmarks, accessible labels, native dialogs, skip-to-content,
  focus-visible outlines, keyboard actions and focus restoration
- Real state filtering, sorting, search, pagination, statuses and empty states
- Original visual tokens, light/dark themes, density, typography and a local
  preference setting that persists theme and density only
- Local create-item form with validation, controlled fields and transient toast
- Browser CSV download with quote escaping and spreadsheet formula guards
- Local synthetic records and no network data requests or telemetry
- Untrusted titles inserted as text nodes, not evaluated as HTML
- Reduced-motion CSS preferences and accessible focus outlines

## Strict evidence boundaries

This is a standalone educational public interface and design system reference,
not a copy of a private employer/client/startup frontend or a hosted production
service. The separate public React/MCP workbench has its own integration and
browser tests. Neither public example proves authorship of all private screens.

Browser acceptance supports concrete behavior but does not alone certify full
WCAG compliance, screen-reader compatibility, comprehensive usability,
performance, security or rights ownership. For employer use, establish
approved designs and content, conduct manual assistive-technology testing and
review all deployment/privacy/accessibility requirements independently.
