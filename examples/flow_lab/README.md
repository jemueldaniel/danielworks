# Flow Laboratory — original accessible graph canvas

This self-contained, privacy-safe JavaScript/CSS/HTML example demonstrates **real UI engineering** beyond a static dashboard: an editable directed graph, pointer dragging, keyboard repositioning, semantic node inspector, bound component names, keyboard command menu, focus-restored dialogs, undo/redo, cycle-safe links, zoom, light/dark and compact modes, local-only restoration, and strictly validated JSON import/export.

All nodes, descriptions, links and graph data are synthetic. **No proprietary product interface, private source, login, customer data, third-party images, analytics, remote script, model call, payment, API request or backend is included.** The localStorage key stores only the demo graph and preferences on this device; exports require a deliberate click and imports are schema-validated. The editor does not evaluate imported data as code or insert user text as HTML.

## Run

From this folder, run `python -B -m http.server 4377 --bind 127.0.0.1` and open `http://127.0.0.1:4377/`. Do not expose this development server to a public interface. Modules require an HTTP origin rather than `file://`.

From the repository root run `node --test --test-reporter=tap examples/flow_lab/test_model.mjs`. No npm packages are required for model tests or the interface. The separate browser test requires Playwright and installed Chromium or Edge (see `projects/flow-lab-tests/browser.test.mjs`).

## Demonstration script

1. Select **Normalize** and change its title and description. The graph displays the new text literally.
2. Tab to the node button; move it with arrow keys, then undo and redo. Mouse/touch users can drag the same node.
3. Create an **output** node, choose its target from another node's inspector and create a directed link. Try a reverse link that would create a cycle; it is rejected.
4. Export the JSON, reset, import the same file and verify the graph is restored without a network call. Try malformed JSON or an extra property; it is rejected.
5. Open commands with Ctrl/⌘+K, filter with a query, activate with Enter, close dialogs with Escape, toggle theme/compact mode and inspect the 320 px layout.

## Proof and limits

Graph model behavior is deterministic and covered by genuine Node tests, including negative inputs, topological cycle rejection, strict portable schema, bounded history and export roundtrip. Browser acceptance is a separate gate; it is not implied by model tests. Keyboard use and automated browser checks do not establish full WCAG compliance, screen-reader certification, production-grade authorization, multi-user collaboration, accessibility research or permission to copy unrelated company designs. Test the installed browsers and accessibility technology required by a real employer. The graph editor stores state in localStorage, not a secure database, and is not a distributed workflow engine.
