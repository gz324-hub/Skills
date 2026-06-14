# Skills

## 📚 Zotero Citation Graph

Turn a Zotero literature review into an **interactive citation map** — every paper
is a dot, arrows show citations, dot **colour = research genre**, dot **size = how
often it's cited in your library**, and **clicking a dot opens the paper**.

| | |
|---|---|
| **▶️ How to run it (start here)** | **[HOW_TO_RUN.md](HOW_TO_RUN.md)** |
| Project & code | [`zotero-citation-graph/`](zotero-citation-graph/) |
| Technical details | [`zotero-citation-graph/README.md`](zotero-citation-graph/README.md) |

![example](zotero-citation-graph/.claude/skills/run-zotero-citation-graph/example.png)

### 30-second version (Windows)

```powershell
cd ~
git clone https://github.com/gz324-hub/Skills.git
cd Skills; git checkout claude/friendly-faraday-qn9hng; cd zotero-citation-graph
python build_graph.py --input sample/oncology.json --out out   # demo
start index.html
```

Then point it at your own library — full walkthrough in **[HOW_TO_RUN.md](HOW_TO_RUN.md)**.
