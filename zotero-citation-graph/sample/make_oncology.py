#!/usr/bin/env python3
"""
make_oncology.py — Generate an oncology demo library + matching CrossRef cache
so build_graph.py produces a colourful, genre-classified citation graph fully
OFFLINE. Titles/abstracts are written to land cleanly in each genre defined by
genres.json (the live path classifies your real papers the same way).

Writes:
    sample/oncology.json         CSL-JSON export (12 papers across genres)
    cache/crossref/<doi>.json    CrossRef-shaped {"message":{"reference":[...]}}
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import build_graph as bg  # noqa: E402

# id -> (title, abstract, authors[(g,f)], year, doi, venue)
PAPERS = {
    "olaparib_trial": (
        "Olaparib maintenance therapy in platinum-sensitive ovarian cancer: a "
        "randomized, double-blind, phase III trial",
        "A randomized double-blind phase III clinical trial evaluating efficacy "
        "and safety of olaparib maintenance.",
        [("M.", "Ledermann")], "2019", "10.1000/onc.0001", "J. Clin. Oncol."),
    "parp_hrd": (
        "PARP inhibition exploits homologous recombination deficiency and "
        "replication stress in BRCA-mutant tumors",
        "PARP inhibitors induce synthetic lethality through unrepaired DNA damage "
        "in homologous recombination deficient cells.",
        [("H.", "Farmer")], "2017", "10.1000/onc.0002", "Nat. Rev. Cancer"),
    "net_method": (
        "An open-source computational framework and algorithm for network "
        "analysis of signaling pathways",
        "We present a scalable computational framework and algorithm implemented "
        "as open-source software for pathway network analysis.",
        [("J.", "Chen")], "2020", "10.1000/onc.0003", "Bioinformatics"),
    "caf_tme": (
        "Cancer-associated fibroblasts shape the tumor microenvironment and "
        "promote immune evasion",
        "Cancer-associated fibroblasts remodel the stroma and extracellular "
        "matrix of the tumor microenvironment.",
        [("E.", "Sahai")], "2018", "10.1000/onc.0004", "Nat. Rev. Cancer"),
    "pd1_immuno": (
        "PD-1 checkpoint blockade enhances T cell-mediated antitumor immunity",
        "Immune checkpoint blockade targeting PD-1 restores T cell antitumor "
        "immunity and durable responses.",
        [("S.", "Topalian")], "2016", "10.1000/onc.0005", "Cell"),
    "scrna_genomics": (
        "Single-cell RNA sequencing reveals transcriptomic heterogeneity across "
        "tumor genomes",
        "Single-cell RNA sequencing exposes genomic and transcriptomic "
        "heterogeneity and somatic mutation patterns.",
        [("A.", "Tirosh"), ("B.", "Izar"), ("S.", "Prakadan"), ("M.", "Wadsworth"),
         ("D.", "Treacy"), ("J.", "Trombetta"), ("A.", "Rotem"), ("C.", "Rodman"),
         ("L.", "Garraway")], "2019", "10.1000/onc.0006", "Science"),
    "hallmarks_review": (
        "The hallmarks of cancer: a review of emerging therapeutic perspectives",
        "A comprehensive review and perspective on the hallmarks of cancer and "
        "emerging therapies.",
        [("D.", "Hanahan")], "2022", "10.1000/onc.0007", "Cancer Discov."),
    "pembro_trial": (
        "Pembrolizumab versus chemotherapy in advanced melanoma: a randomized "
        "phase III clinical trial",
        "A randomized phase III clinical trial comparing pembrolizumab with "
        "chemotherapy for efficacy and safety.",
        [("C.", "Robert")], "2015", "10.1000/onc.0008", "N. Engl. J. Med."),
    "atm_atr_ddr": (
        "ATM and ATR kinase signaling coordinate the DNA damage response to "
        "double-strand breaks",
        "ATM and ATR kinase signaling orchestrate the DNA damage response and "
        "repair of double-strand breaks.",
        [("S.", "Jackson")], "2017", "10.1000/onc.0009", "Mol. Cell"),
    "hypoxia_tme": (
        "Hypoxia and angiogenesis in the tumor microenvironment drive metastatic "
        "progression",
        "Hypoxia drives angiogenesis within the tumor microenvironment, promoting "
        "metastasis and niche remodeling.",
        [("P.", "Carmeliet")], "2018", "10.1000/onc.0010", "Nat. Rev. Cancer"),
    "graph_method": (
        "A scalable algorithm and software toolkit for graph-based analysis of "
        "biological networks",
        "An efficient algorithm and software toolkit enabling benchmark "
        "graph-based analysis of large biological networks.",
        [("R.", "Kumar")], "2021", "10.1000/onc.0011", "Bioinformatics"),
    "wgs_genomics": (
        "Whole-genome sequencing identifies driver mutations and variant "
        "signatures across cancers",
        "Whole-genome sequencing reveals recurrent driver mutations and variant "
        "signatures, with multi-omics integration.",
        [("M.", "Stratton")], "2020", "10.1000/onc.0012", "Nature"),
}

# citing id -> [cited ids]  (later/derivative work cites foundational work)
CITES = {
    "olaparib_trial": ["parp_hrd", "hallmarks_review", "atm_atr_ddr"],
    "parp_hrd": ["atm_atr_ddr", "hallmarks_review"],
    "net_method": ["atm_atr_ddr", "hallmarks_review"],
    "caf_tme": ["hallmarks_review", "pd1_immuno"],
    "pd1_immuno": ["hallmarks_review"],
    "scrna_genomics": ["hallmarks_review", "wgs_genomics"],
    "pembro_trial": ["pd1_immuno", "hallmarks_review"],
    "atm_atr_ddr": ["hallmarks_review"],
    "hypoxia_tme": ["caf_tme", "hallmarks_review"],
    "graph_method": ["net_method", "scrna_genomics"],
    "wgs_genomics": ["hallmarks_review"],
}


def main():
    csl = []
    for pid, (title, abstract, authors, year, doi, venue) in PAPERS.items():
        csl.append({
            "id": pid, "type": "article-journal", "title": title,
            "abstract": abstract,
            "author": [{"given": g, "family": f} for g, f in authors],
            "issued": {"date-parts": [[int(year)]]},
            "DOI": doi, "container-title": venue, "URL": "",
        })
    with open(os.path.join(HERE, "oncology.json"), "w", encoding="utf-8") as fh:
        json.dump(csl, fh, indent=2, ensure_ascii=False)

    cache_dir = os.path.join(ROOT, "cache")
    doi_of = {pid: bg._norm_doi(p[4]) for pid, p in PAPERS.items()}
    for pid in PAPERS:
        refs = [{"DOI": doi_of[t]} for t in CITES.get(pid, [])]
        payload = {"message": {"DOI": doi_of[pid], "reference": refs}}
        cp = bg._cache_path(cache_dir, doi_of[pid])
        os.makedirs(os.path.dirname(cp), exist_ok=True)
        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    print("Wrote sample/oncology.json (%d papers) and %d CrossRef cache files."
          % (len(csl), len(PAPERS)))


if __name__ == "__main__":
    main()
