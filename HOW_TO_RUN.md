# How to Run the Zotero Citation Graph

This turns your Zotero literature review into an **interactive map**: every dot is
a paper, arrows show which paper cites which, the **colour** of a dot is the
paper's research genre (Clinical trial, DDR, TME, …), the **size** of a dot is how
often it's cited within your own library, and **clicking a dot opens that paper's
website**.

> The whole project lives in the **`zotero-citation-graph/`** folder of this repo.
> Everything below is written for **Windows** (since that's what you're on); the
> notes at the bottom cover Mac/Linux.

---

## What you need (one-time installs)

| Tool | Why | Get it |
|------|-----|--------|
| **Git** | to download the project | https://git-scm.com/download/win |
| **Python 3** | to build the graph from your library | https://www.python.org/downloads/ — on the **first installer screen, tick "Add python.exe to PATH"** |
| A **web browser** | to view the graph | you already have one |

> You do **not** need Node.js, npm, or Playwright for normal use — those are only
> for the automated screenshot tool used by developers.

Check they're installed (open a **new** PowerShell window after installing):

```powershell
git --version
python --version
```

Both should print a version number. If `python` prints nothing, try `py --version`
and use `py` instead of `python` everywhere below.

---

## Step 1 — Download the project (one-time)

Open **PowerShell** (Start menu → type "PowerShell") and run:

```powershell
cd ~
git clone https://github.com/gz324-hub/Skills.git
cd Skills
git checkout claude/friendly-faraday-qn9hng
cd zotero-citation-graph
```

The project is now at **`C:\Users\<YourName>\Skills\zotero-citation-graph`**.

*(Already downloaded it before? Just update it — see [Updating](#updating-to-the-latest-version) at the bottom.)*

---

## Step 2 — See it work right away (sample data)

A ready-made example is included, so you can look before using your own papers:

```powershell
python build_graph.py --input sample/oncology.json --out out
start index.html
```

Your browser opens a coloured citation graph of 12 cancer-research papers. Try it:
**hover** a dot for details, **click** a dot to open the paper, **click a genre** in
the legend to highlight just those papers, **drag** dots around, **scroll** to zoom.

---

## Step 3 — Use your own Zotero library

### 3a. Export from Zotero
1. In Zotero, click the collection (or library) you want to map.
2. **Right-click it → Export Collection…**
3. Set **Format = CSL JSON**, click OK.
4. In the save dialog, browse to
   `C:\Users\<YourName>\Skills\zotero-citation-graph` and save it as
   **`My Library.json`**.

> 💡 The file must end up **inside the `zotero-citation-graph` folder** (next to
> `build_graph.py`). If you save it elsewhere, just use its full path in the next
> command, e.g. `--input "C:\Users\<YourName>\Downloads\My Library.json"`.

### 3b. Build the graph (with citation links)

```powershell
python build_graph.py --input "My Library.json" --out out --online --mailto gz324@cam.ac.uk
```

- `--online` fetches the "who cites whom" data from **CrossRef** over the internet.
- It pauses ~1 second between papers to be polite to the free service, so the
  **first** run on a big library can take a minute or two. It prints a summary like
  `Graph: 84 papers, 142 citation edges`.
- Every lookup is **cached** in the `cache/` folder, so future runs are fast.

### 3c. Open it

```powershell
start index.html
```

Your own papers now fill the graph. 🎉

---

## Updating it later ("refresh every now and then")

Whenever you add papers in Zotero, re-export over the same `My Library.json`
(Step 3a) and run Step 3b again. Because citation lookups are cached, only the new
papers are fetched — it's quick.

---

## Customising the genre colours

Genres and their colours live in **`genres.json`** (open it in Notepad or any text
editor). Each paper is put into the **first** genre whose keywords appear in its
title/abstract — so the order is the priority, and **`Other`** at the bottom catches
anything unmatched (this is what keeps every paper in exactly one genre).

To adapt it to your field: edit the keyword lists, rename genres, change the
`color` hex codes, or reorder them. Then rebuild (Step 3b) and refresh the page.

```json
{ "name": "DDR", "color": "#2e6fdb",
  "match": ["dna damage", "homologous recombination", "parp", "brca", "atr kinase"] }
```

---

## Things to know

- **Citation arrows need DOIs.** Arrows are reconstructed from each paper's DOI via
  CrossRef. Keep DOIs filled in for your papers in Zotero — papers without a DOI
  still show up as dots, but with no auto-discovered citations.
- **An arrow only appears when *both* papers are in your library.** Citations to
  papers you haven't saved aren't drawn — that's normal, and keeps the map about
  *your* collection.
- **`--online` needs internet.** Offline, you'll see the dots but few/no arrows.

---

## Troubleshooting

| Message | What it means / fix |
|---------|---------------------|
| `FileNotFoundError: 'My Library.json'` | The file isn't in the folder you ran the command from. Run `Get-ChildItem *.json` to see what's there, or point `--input` at the file's full path. |
| `python : The term 'python' is not recognized` | Python isn't installed or wasn't added to PATH. Reinstall Python and tick **"Add python.exe to PATH"**, then open a new PowerShell. (Or use `py` instead of `python`.) |
| `Graph: N papers, 0 citation edges` | Your papers have no DOIs, or you ran without `--online`. Add DOIs in Zotero and rebuild with `--online`. |
| Browser shows **"No graph data"** | You haven't built it yet — run the `python build_graph.py …` command first, then refresh. |
| All dots are the **"Other"** colour | The genre keywords in `genres.json` don't match your field — edit them (see *Customising* above). |

---

## Mac / Linux

Same idea, different "open" command. From inside `zotero-citation-graph/`:

```bash
python3 build_graph.py --input "My Library.json" --out out --online --mailto gz324@cam.ac.uk
open index.html        # macOS   (Linux: xdg-open index.html)
```

There's also a helper script: `./refresh.sh "My Library.json"` (add
`ONLINE=1 MAILTO=you@uni.edu` in front to fetch citations).

---

## Updating to the latest version

If you already cloned the repo earlier and want the newest changes:

```powershell
cd ~\Skills\zotero-citation-graph
git checkout -- out                 # discard the auto-generated graph (it's rebuilt anyway)
git fetch origin
git checkout claude/friendly-faraday-qn9hng
git pull origin claude/friendly-faraday-qn9hng
```

Your own `My Library.json` and `cache/` are left untouched. Then rebuild (Step 3b).
