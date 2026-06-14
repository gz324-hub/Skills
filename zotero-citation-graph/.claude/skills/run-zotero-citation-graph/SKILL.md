---
name: run-zotero-citation-graph
description: Build, run, refresh, and screenshot the Zotero citation graph — an interactive plot where nodes are papers, arrows are citations, and clicking a node opens the paper. Use when asked to run/build/refresh the citation graph, view the Zotero literature-review graph, regenerate graph.json from a Zotero export, or screenshot the viewer.
---

Interactive citation graph built from a Zotero export: nodes = papers, a
directed edge **A → B** = "A cites B", node size = times cited within the
library, clicking a node opens its DOI/URL. The viewer is one self-contained
HTML file (vis-network is vendored — no CDN, no server). Drive it headless via
`.claude/skills/run-zotero-citation-graph/driver.mjs` (Playwright Chromium):
it renders the graph, screenshots it, and asserts that a node-click opens the
right paper URL.

All paths below are relative to `zotero-citation-graph/` (the unit dir).

## Prerequisites

No `apt-get` needed — this container already has Python 3.11, Node 22, and a
Playwright Chromium under `/opt/pw-browsers`. The only install is the Playwright
JS package (the browser binary is already present, so skip its download):

```bash
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install
```

On a normal machine (where the browser isn't preinstalled) drop the env var so
Playwright downloads its own Chromium: `npm install`.

`build_graph.py` itself has **zero** third-party deps (stdlib only), so the
pipeline runs without `npm install`.

## Build

The graph data is generated from a Zotero export. For the bundled demo, first
materialise the sample library + its cached citation data, then build:

```bash
python3 sample/make_sample.py
python3 build_graph.py --input sample/library.json --out out
```

This writes `out/graph.json` and `out/graph-data.js` (the viewer reads the `.js`
form so it works over `file://` with no server). Expected:
`10 papers, 18 citation edges`.

To refresh from a real export (re-run "every now and then"):

```bash
./refresh.sh "sample/library.json"                          # offline, cache-only
ONLINE=1 MAILTO=gz324@cam.ac.uk ./refresh.sh "sample/library.json"   # top up from CrossRef
```

## Run (agent path)

Drive the viewer headless with the driver. It auto-detects the Chromium under
`/opt/pw-browsers`, loads `index.html` over `file://`, waits for the layout to
stabilise, and screenshots to `out/screenshot.png`.

```bash
# full smoke: render + screenshot + assert a node-click opens its paper URL
node .claude/skills/run-zotero-citation-graph/driver.mjs verify
```

Chrome prints SSL handshake noise to stderr (telemetry phoning home, blocked in
this network) — it's harmless. Filter it:

```bash
node .claude/skills/run-zotero-citation-graph/driver.mjs verify 2>&1 \
  | grep -vE 'handshake failed|ssl_client_socket|net_error|ERROR:net/socket'
```

`verify` prints `PASS ✅` and writes `out/screenshot.png`. **Look at it** — you
should see labelled paper nodes, arrows pointing from citing → cited papers, and
the most-cited paper as the largest/reddest hub.

Other commands:

```bash
# just screenshot (optionally to a custom path)
node .claude/skills/run-zotero-citation-graph/driver.mjs shot /tmp/custom-shot.png

# click the node matching a query, report the URL it opens
node .claude/skills/run-zotero-citation-graph/driver.mjs click "residual"
#  → • clicked "He 2016" → https://doi.org/10.1109/cvpr.2016.90
```

Override the browser with `CHROME_BIN=/path/to/chrome`, the unit dir with
`ROOT=...`, the screenshot path with `OUT=...`.

## Run (human path)

No server needed — open the file directly:

```bash
# the build / refresh step prints this link:
echo "file://$(pwd)/index.html"
```

Open that `file://…/index.html` in any browser. Drag nodes, scroll to zoom,
type in the filter box, **click a node to open the paper**. (Headless, this path
shows nothing — use the driver above.)

## Gotchas

- **Zotero exports contain no citation graph.** Edges are reconstructed from
  CrossRef reference lists keyed by **DOI**. Papers without a DOI still render
  as nodes but get no auto-discovered citation edges. Tell users to keep DOIs
  populated in Zotero.
- **External HTTP is blocked in this container (403)** — CrossRef, OpenCitations,
  Semantic Scholar, and every CDN. So: (1) vis-network is **vendored** into
  `vendor/` rather than loaded from a CDN, and (2) the demo's citation data is
  pre-cached under `cache/crossref/` so `--online` isn't required here. The same
  code path fetches live from CrossRef on a networked machine.
- **`--online` fails gracefully.** On a cache miss with no network it logs
  `! CrossRef fetch failed … 403`, keeps going, and reports `0 edges` with a
  hint — it does not crash.
- **Playwright/browser version skew.** The installed Playwright (1.56) wants
  `chromium-1223`, but only `chromium-1194` is present. The driver works around
  this by passing `executablePath` to the binary it actually finds — do **not**
  rely on `chromium.launch()` with no `executablePath` here (it errors
  "Executable doesn't exist").
- **ESM ignores `NODE_PATH`.** You cannot import the globally-installed
  Playwright from an `.mjs` via `NODE_PATH=$(npm root -g)`. You must
  `npm install` it into the unit (module resolution then walks up from the skill
  dir to `zotero-citation-graph/node_modules`).
- **vis-network draws to `<canvas>`**, so nodes are *not* DOM elements you can
  `page.click("…")`. The driver computes screen coordinates with
  `network.getPositions()` + `network.canvasToDOM()` and clicks the pixel.
- **Click verification intercepts `window.open`.** `driver.mjs` injects an
  `addInitScript` that records `window.open(url)` into `window.__opened` instead
  of spawning real tabs, then asserts the captured URL equals the node's `url`.
- **`file://` + `fetch()` is CORS-blocked**, which is why the pipeline emits
  `graph-data.js` (`window.GRAPH = …`) instead of a `.json` the page fetches.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Graph: … 0 citation edges` | Papers lack DOIs, or cache is empty. Run `ONLINE=1 MAILTO=you@uni.edu ./refresh.sh your.json` to fetch from CrossRef. |
| `index.html not found` / viewer shows "No graph data" | Build first: `python3 build_graph.py --input sample/library.json --out out`. |
| Playwright `Executable doesn't exist …chromium-1223…` | The driver auto-detects `/opt/pw-browsers/chromium-*`; if yours is elsewhere set `CHROME_BIN=/path/to/chrome`. |
| `ERR_MODULE_NOT_FOUND: 'playwright'` | Run `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install` inside `zotero-citation-graph/`. |
| Driver prints `(nothing opened!)` | Graph wasn't built or didn't stabilise — rebuild, then re-run `verify`. |
| Chrome `handshake failed … net_error -202` spam | Harmless telemetry; pipe through the `grep -vE` filter shown above. |

## The harness

`driver.mjs` (in this skill dir) is the committed harness — a Playwright wrapper
exposing `verify` / `shot` / `click`. `example.png` here is a reference of a
correct render. The graph pipeline is `../../../build_graph.py`; the viewer is
`../../../index.html`.
