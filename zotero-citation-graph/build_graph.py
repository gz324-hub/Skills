#!/usr/bin/env python3
"""
build_graph.py — Turn a Zotero export into an interactive citation graph.

Pipeline:  Zotero export  ->  nodes (papers) + directed edges (A cites B)  ->
           out/graph-data.js  (consumed by index.html, opens over file://)
           out/graph.json     (portable copy of the same data)

A node is a paper. A directed edge A -> B means "paper A cites paper B"
(arrow points from the citing paper to the cited paper). Clicking a node in
the viewer opens that paper's website (DOI / URL).

Citation edges are NOT present in a vanilla Zotero export, so they are
enriched from CrossRef reference lists, keyed by DOI. Responses are cached
under --cache so reruns ("refresh every now and then") are incremental and
the graph can be rebuilt fully offline from the cache.

Stdlib only. Online enrichment uses urllib (no third-party deps required).

Usage:
    python3 build_graph.py --input sample/library.json --out out
    python3 build_graph.py --input sample/library.json --out out --online \
        --mailto you@example.com
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone


# ----------------------------- input parsing ------------------------------

def _slug(text, n=80):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s or "untitled")[:n]


def _norm_doi(doi):
    if not doi:
        return ""
    doi = doi.strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.I)
    return doi.lower()


def detect_format(path, explicit):
    if explicit and explicit != "auto":
        return explicit
    if path.lower().endswith((".json", ".csljson")):
        return "csljson"
    if path.lower().endswith((".bib", ".bibtex")):
        return "bibtex"
    # sniff
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        head = fh.read(2048).lstrip()
    return "csljson" if head.startswith(("[", "{")) else "bibtex"


def _people(authors):
    """CSL author list -> 'Lastname, Lastname2'."""
    out = []
    for a in authors or []:
        fam = a.get("family") or a.get("literal") or ""
        if fam:
            out.append(fam)
    return out


def parse_csljson(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        data = json.load(fh)
    if isinstance(data, dict):  # some exporters wrap in {"items":[...]}
        data = data.get("items", data.get("references", []))
    items = []
    for it in data:
        issued = it.get("issued", {}) or {}
        year = ""
        dp = issued.get("date-parts")
        if dp and dp[0]:
            year = str(dp[0][0])
        elif issued.get("raw"):
            m = re.search(r"\d{4}", issued["raw"])
            year = m.group(0) if m else ""
        items.append({
            "title": (it.get("title") or "").strip(),
            "authors": _people(it.get("author")),
            "year": year,
            "doi": _norm_doi(it.get("DOI")),
            "url": (it.get("URL") or "").strip(),
            "type": it.get("type") or "",
            "venue": (it.get("container-title") or it.get("publisher") or "").strip(),
        })
    return items


_BIB_ENTRY = re.compile(r"@(\w+)\s*\{([^,]*),(.*?)\n\}", re.S)
_BIB_FIELD = re.compile(r"(\w+)\s*=\s*[{\"](.*?)[}\"]\s*,?\s*\n", re.S)


def parse_bibtex(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    items = []
    for etype, _key, body in _BIB_ENTRY.findall(text):
        fields = {k.lower(): re.sub(r"\s+", " ", v).strip()
                  for k, v in _BIB_FIELD.findall(body + "\n")}
        authors = [p.strip().split(",")[0].strip()
                   for p in re.split(r"\s+and\s+", fields.get("author", ""))
                   if p.strip()]
        items.append({
            "title": fields.get("title", "").strip("{} "),
            "authors": authors,
            "year": fields.get("year", ""),
            "doi": _norm_doi(fields.get("doi")),
            "url": fields.get("url", ""),
            "type": etype.lower(),
            "venue": fields.get("journal") or fields.get("booktitle") or "",
        })
    return items


def load_items(path, fmt):
    fmt = detect_format(path, fmt)
    items = parse_csljson(path) if fmt == "csljson" else parse_bibtex(path)
    # stable id: DOI if present, else slug of title
    seen = {}
    for it in items:
        base = it["doi"] or _slug(it["title"])
        nid = base
        i = 2
        while nid in seen:
            nid = f"{base}-{i}"
            i += 1
        seen[nid] = True
        it["id"] = nid
    return items, fmt


# --------------------------- citation enrichment --------------------------

def _cache_path(cache_dir, doi):
    return os.path.join(cache_dir, "crossref", _slug(doi, 200) + ".json")


def crossref_references(doi, cache_dir, online, mailto, sleep=1.0):
    """Return list of cited DOIs for `doi`, using cache first."""
    cp = _cache_path(cache_dir, doi)
    payload = None
    if os.path.exists(cp):
        try:
            with open(cp, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception:
            payload = None
    if payload is None and online:
        url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
        ua = "zotero-citation-graph/1.0 (mailto:%s)" % (mailto or "anonymous@example.com")
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            os.makedirs(os.path.dirname(cp), exist_ok=True)
            with open(cp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            time.sleep(sleep)  # be polite to the public API
        except Exception as exc:
            sys.stderr.write("  ! CrossRef fetch failed for %s: %s\n" % (doi, exc))
            payload = None
    if not payload:
        return None  # unknown (no cache, offline or fetch failed)
    refs = (payload.get("message", {}) or {}).get("reference", []) or []
    out = []
    for r in refs:
        d = _norm_doi(r.get("DOI"))
        if d:
            out.append(d)
    return out


# ------------------------------- graph build ------------------------------

def build(items, cache_dir, online, mailto):
    by_doi = {it["doi"]: it["id"] for it in items if it["doi"]}
    edges, seen_edge = [], set()
    resolved, unknown = 0, 0
    for it in items:
        if not it["doi"]:
            unknown += 1
            continue
        refs = crossref_references(it["doi"], cache_dir, online, mailto)
        if refs is None:
            unknown += 1
            continue
        resolved += 1
        for ref_doi in refs:
            tgt = by_doi.get(ref_doi)
            if tgt and tgt != it["id"]:
                key = (it["id"], tgt)
                if key not in seen_edge:
                    seen_edge.add(key)
                    edges.append({"from": it["id"], "to": tgt})

    indeg = {}
    for e in edges:
        indeg[e["to"]] = indeg.get(e["to"], 0) + 1

    nodes = []
    for it in items:
        cited_by = indeg.get(it["id"], 0)
        first = it["authors"][0] if it["authors"] else "?"
        label = "%s %s" % (first, it["year"] or "")
        # click target: DOI page, else stored URL, else Scholar search
        if it["doi"]:
            link = "https://doi.org/" + it["doi"]
        elif it["url"]:
            link = it["url"]
        else:
            link = "https://scholar.google.com/scholar?q=" + urllib.parse.quote(it["title"])
        nodes.append({
            "id": it["id"],
            "label": label.strip(),
            "title": it["title"],
            "authors": ", ".join(it["authors"]),
            "year": it["year"],
            "venue": it["venue"],
            "doi": it["doi"],
            "url": link,
            "cited_by": cited_by,
            "value": 1 + cited_by,  # node size scales with in-library citations
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "stats": {
            "papers": len(nodes),
            "edges": len(edges),
            "refs_resolved": resolved,
            "refs_unknown": unknown,
        },
    }


# --------------------------------- output ---------------------------------

def write_outputs(graph, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "graph.json"), "w", encoding="utf-8") as fh:
        json.dump(graph, fh, indent=2, ensure_ascii=False)
    # JS form lets index.html load over file:// with no server / no CORS
    with open(os.path.join(out_dir, "graph-data.js"), "w", encoding="utf-8") as fh:
        fh.write("window.GRAPH = ")
        json.dump(graph, fh, ensure_ascii=False)
        fh.write(";\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Zotero export -> citation graph")
    ap.add_argument("--input", required=True, help="Zotero export (CSL-JSON or BibTeX)")
    ap.add_argument("--out", default="out", help="output dir (default: out)")
    ap.add_argument("--cache", default="cache", help="citation cache dir (default: cache)")
    ap.add_argument("--format", default="auto", choices=["auto", "csljson", "bibtex"])
    ap.add_argument("--online", action="store_true",
                    help="fetch missing reference lists from CrossRef (else cache-only)")
    ap.add_argument("--mailto", default="", help="contact email for the CrossRef polite pool")
    args = ap.parse_args(argv)

    items, fmt = load_items(args.input, args.format)
    print("Loaded %d papers from %s (%s)" % (len(items), args.input, fmt))
    graph = build(items, args.cache, args.online, args.mailto)
    write_outputs(graph, args.out)
    s = graph["stats"]
    print("Graph: %d papers, %d citation edges "
          "(refs resolved for %d, unknown for %d)"
          % (s["papers"], s["edges"], s["refs_resolved"], s["refs_unknown"]))
    print("Wrote %s/graph.json and %s/graph-data.js" % (args.out, args.out))
    if s["edges"] == 0:
        print("NOTE: 0 edges. Run with --online --mailto you@example.com to "
              "fetch citation data from CrossRef (needs DOIs + network).",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
