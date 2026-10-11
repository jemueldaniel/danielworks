# Signal Study — an original interactive visual analytics laboratory

Signal Study is an independent, responsive HTML/CSS/JavaScript example of
interactive data visualization. It does **not** copy or disclose any private
product, company branding, client assets, trade secrets, databases, customer
records, business strategy, endpoint, credentials or unreleased interface.
All channel names, numerical series, conversions and cohorts are invented.

## Actual interactions

- Four independently drawn SVG data modes: week-by-week trends, stacked channel
  comparison, fictional retention cohorts, and fictional conversion funnel.
- Segment, time-window, and focus-week filters; actual metric recomputation;
  responsive data inspection; selectable table rows and keyboard navigation.
- Browser-local annotations with text validation, length and count limits,
  safe literal rendering, deletion, and spreadsheet-formula-safe CSV export.
- Original UI, light/dark appearance preference, compact density, focus/keyboard
  controls, accessible SVG text summary, reduced-motion styling and Escape dialogs.
- Client-side CSV and SVG downloads. No API, authentication, analytics, third-
  party fonts, CDN, cookies, tracking pixels or network-fetching code.

Run without installation from this directory:

```sh
python -B -m http.server 4323 --bind 127.0.0.1
# Open http://127.0.0.1:4323 in a modern browser.
```

From the full `danielworks` repository, run:

```sh
node --test --test-reporter=tap examples/data_studio/test_model.mjs
npm run test:data-studio
```

The pure-state Node suite can be exported and executed through `data-studio`
profile in the source-pinned one-shot builder. Browser acceptance requires the
full repository's locked Playwright and an **already installed** Edge/Chromium.
The HTTP test harness binds to 127.0.0.1 with an explicit five-resource
allowlist, no external requests, and defensive CSP. An installed browser is
not fetched or bootstrapped automatically.

This is a deliberately **educational offline reference**, not a production
analytics service, genuine cohort model, representative measurement from real
users, private UI reproduction, production dataset validation, visual
accessibility certification or independent legal/security review. Source tests
and hosted deployment are different qualifications. Review source ownership,
privacy, requirements, accessibility and operations independently before reuse.
