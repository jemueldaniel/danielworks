# Reusable frontend and UI/UX evidence matrix

This matrix maps generic public implementation to actual reproducible tests.
It deliberately does not imply that private product UI or business logic has
been copied into the public showcase.

| Capability | Original public reference | Executable proof | Qualification |
|---|---|---|---|
| Responsive layout | examples/interface_lab/index.html and style.css | projects/interface-lab-tests/browser.test.mjs checks 320, 390, 768 and 1280px widths | Representative viewports, not every device |
| Accessibility primitives | Semantic landmarks, named navigation, focus, native dialog | Keyboard, mobile menu and focus restoration browser tests | No full screen-reader/WCAG certification |
| Data tables and UI state | examples/interface_lab/model.mjs and app.mjs | Node state tests and real browser filtering/pagination | Synthetic local data only |
| Form lifecycle and feedback | Native form and validation states | Real browser create, invalid submission and Escape tests | No backend accounts |
| Themes and density | CSS tokens and local-only preferences | Browser theme and density reload acceptance | Additional contrast audit needed |
| Safe untrusted rendering | textContent and CSV quoting/guards | Real markup and CSV download test cases | Not a complete XSS/security audit |
| Keyboard productivity | Shortcuts, skip navigation and quick actions | Real browser shortcut and palette tests | No OS accessibility certification |
| Full-stack React | Separate public evidence-workbench project | Strict TypeScript, MCP/API and seven Edge browser tests | Not production-hosted or all private apps |
| One-command reuse | Approved interface-lab public-only profile | Fixed model tests and byte-verified exported starter | Browser suite requires installed dependencies |

## Demonstration workflow

Check out the exact public commit. Obtain the SHA-256 of its
SOURCE_MANIFEST.json independently. Run the state-model and real browser tests.
Open the localhost UI, search for an impossible term to demonstrate the empty
state, create an item, switch theme, exercise mobile nav and export a CSV.
Run the one-command public assembler with the interface-lab profile into a
fresh directory and preserve its test receipt and output hashes.

## Protecting private work

Only independent generic UI and state models should be published. Do not
transfer startup names, private repository files, confidential client screens,
business logic, unpublished assets, API keys, local home paths or customer
records. File-count inventory and pattern-based scanning are not proof of
individual authorship, license clearance or production quality. Every
separate capability needs its own explicit demonstration and qualification.

## Multi-domain frontend coverage added by UI Atlas

[UI Atlas](../examples/ui_atlas/README.md) expands beyond dashboards:
fictional commerce/cart, in-memory Kanban, synthetic chat, editorial
marketing/onboarding, and component token export. See the
[Atlas source and acceptance matrix](ATLAS_FRONTEND_COVERAGE.md).
The Node model suite covers 65 tests and installed Edge covers twenty
interaction tests at five viewport widths. No private screenshots or
startup product designs were copied. These are tested original UI
examples, not claims of complete historical UI authorship or UX certification.
