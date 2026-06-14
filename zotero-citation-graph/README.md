# Zotero Citation Graph

Turn a Zotero literature-review export into an **interactive citation graph**:

- every **node** is a paper,
- a directed **edge A → B** means *paper A cites paper B*,
- node **colour** = the paper's **research genre** (Clinical trial / DDR / TME /
  Immunotherapy / Genomics / Method / Review / … — editable in `genres.json`),
- node **size** = how often a paper is cited *within your library*,
- **clicking a node opens that paper's website** (its DOI page / URL),
- it's a single self-contained HTML file on a clean white canvas —
  **double-click `index.html`**, no server.

![example](.claude/skills/run-zotero-citation-graph/example.png)

> 👉 **New here? Read [../HOW_TO_RUN.md](../HOW_TO_RUN.md) for the step-by-step guide
> (Windows & Mac).** The notes below are the technical reference.

## Quick start

```bash
# 1. (demo) generate the bundled oncology sample + cached citation data
python3 sample/make_oncology.py

# 2. build the graph
python3 build_graph.py --input sample/oncology.json --out out

# 3. open the viewer  (file://<this-dir>/index.html)
```

## Use your own library

1. In Zotero: select your collection → right-click → **Export Collection** →
   format **CSL JSON** (or **BibTeX**). Save it, e.g. `My Library.json`.
2. Build / refresh (re-run "every now and then" as you add papers):

   ```bash
   # offline: rebuild from whatever citations are already cached
   ./refresh.sh "My Library.json"

   # online: also fetch NEW citation links from CrossRef (needs DOIs + network)
   ONLINE=1 MAILTO=you@uni.edu ./refresh.sh "My Library.json"
   ```

## How it works

- **Citation edges.** Zotero exports do **not** contain a citation graph. For each
  paper with a **DOI**, `build_graph.py` looks up its reference list from
  [CrossRef](https://www.crossref.org/) and draws an edge to every referenced paper
  that is *also in your library*. Responses are cached under `cache/`, so the graph
  rebuilds offline. Papers without a DOI still appear (just without auto-citations).
- **Genres (node colour).** Each paper is assigned to exactly one genre by the
  ordered keyword rules in **`genres.json`** — the *first* matching rule wins, and
  the `Other` catch-all makes the set mutually exclusive + collectively exhaustive.
  Matching runs over title + abstract + keywords. Edit `genres.json` to fit your
  field (rename genres, change colours, tweak keywords, reorder priority). A paper
  whose Zotero tag exactly equals a genre name is forced into that genre.

## Files

| Path | What |
|------|------|
| `build_graph.py` | pipeline: Zotero export → `out/graph-data.js` + `out/graph.json` |
| `genres.json` | editable genre → colour → keyword rules (node colouring) |
| `index.html` | the interactive viewer (vis-network, vendored — offline, white theme) |
| `refresh.sh` | rebuild from an export (the "refresh every now and then" entry point) |
| `sample/` | sample libraries (`oncology.json` shows genres; `library.json` is ML) + generators |
| `cache/crossref/` | cached CrossRef reference lists (incremental, offline-friendly) |
| `vendor/` | vis-network bundle (no CDN needed) |

See `.claude/skills/run-zotero-citation-graph/SKILL.md` for the headless
build/screenshot harness.
