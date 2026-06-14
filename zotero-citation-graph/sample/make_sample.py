#!/usr/bin/env python3
"""
make_sample.py — Generate a realistic sample Zotero export + matching CrossRef
cache, so `build_graph.py` produces a real, connected citation graph fully
OFFLINE (this repo's demo path; the live path fetches the same shape from
CrossRef).

Writes:
    sample/library.json          a CSL-JSON Zotero export (10 deep-learning papers)
    cache/crossref/<doi>.json    CrossRef-shaped {"message":{"reference":[...]}}

The cache files are written via build_graph._cache_path so their names match
exactly what the pipeline reads.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import build_graph as bg  # noqa: E402

# id -> (title, authors[(given,family)], year, doi, venue, type, url)
PAPERS = {
    "krizhevsky2017": (
        "ImageNet classification with deep convolutional neural networks",
        [("Alex", "Krizhevsky"), ("Ilya", "Sutskever"), ("Geoffrey E.", "Hinton")],
        "2017", "10.1145/3065386", "Communications of the ACM", "article-journal", ""),
    "lecun2015": (
        "Deep learning",
        [("Yann", "LeCun"), ("Yoshua", "Bengio"), ("Geoffrey", "Hinton")],
        "2015", "10.1038/nature14539", "Nature", "article-journal", ""),
    "he2016": (
        "Deep residual learning for image recognition",
        [("Kaiming", "He"), ("Xiangyu", "Zhang"), ("Shaoqing", "Ren"), ("Jian", "Sun")],
        "2016", "10.1109/CVPR.2016.90", "Proc. CVPR", "paper-conference", ""),
    "szegedy2015": (
        "Going deeper with convolutions",
        [("Christian", "Szegedy"), ("Wei", "Liu"), ("Yangqing", "Jia")],
        "2015", "10.1109/CVPR.2015.7298594", "Proc. CVPR", "paper-conference", ""),
    "mnih2015": (
        "Human-level control through deep reinforcement learning",
        [("Volodymyr", "Mnih"), ("Koray", "Kavukcuoglu"), ("David", "Silver")],
        "2015", "10.1038/nature14236", "Nature", "article-journal", ""),
    "silver2016": (
        "Mastering the game of Go with deep neural networks and tree search",
        [("David", "Silver"), ("Aja", "Huang"), ("Chris J.", "Maddison")],
        "2016", "10.1038/nature16961", "Nature", "article-journal", ""),
    "silver2017": (
        "Mastering the game of Go without human knowledge",
        [("David", "Silver"), ("Julian", "Schrittwieser"), ("Karen", "Simonyan")],
        "2017", "10.1038/nature24270", "Nature", "article-journal", ""),
    "goodfellow2020": (
        "Generative adversarial networks",
        [("Ian", "Goodfellow"), ("Jean", "Pouget-Abadie"), ("Mehdi", "Mirza")],
        "2020", "10.1145/3422622", "Communications of the ACM", "article-journal", ""),
    "hinton2012": (
        "Deep neural networks for acoustic modeling in speech recognition",
        [("Geoffrey", "Hinton"), ("Li", "Deng"), ("Dong", "Yu")],
        "2012", "10.1109/MSP.2012.2205597", "IEEE Signal Processing Magazine",
        "article-journal", ""),
    "schmidhuber2015": (
        "Deep learning in neural networks: An overview",
        [("Jurgen", "Schmidhuber")],
        "2015", "10.1016/j.neunet.2014.09.003", "Neural Networks", "article-journal", ""),
}

# citing id -> [cited ids]  (real-ish citation relationships within the set)
CITES = {
    "lecun2015": ["krizhevsky2017", "hinton2012", "mnih2015"],
    "schmidhuber2015": ["krizhevsky2017", "hinton2012", "mnih2015"],
    "he2016": ["krizhevsky2017", "szegedy2015"],
    "szegedy2015": ["krizhevsky2017"],
    "mnih2015": ["krizhevsky2017", "hinton2012"],
    "silver2016": ["mnih2015", "krizhevsky2017"],
    "silver2017": ["silver2016", "mnih2015", "he2016"],
    "goodfellow2020": ["krizhevsky2017", "hinton2012"],
}

# a couple of out-of-library DOIs to prove the pipeline filters to in-library only
NOISE = ["10.1162/neco.1997.9.8.1735", "10.1126/science.aaa8415"]


def main():
    # 1) CSL-JSON export
    csl = []
    for pid, (title, authors, year, doi, venue, typ, url) in PAPERS.items():
        csl.append({
            "id": pid,
            "type": typ,
            "title": title,
            "author": [{"given": g, "family": f} for g, f in authors],
            "issued": {"date-parts": [[int(year)]]},
            "DOI": doi,
            "container-title": venue,
            "URL": url,
        })
    with open(os.path.join(HERE, "library.json"), "w", encoding="utf-8") as fh:
        json.dump(csl, fh, indent=2, ensure_ascii=False)

    # 2) CrossRef-shaped cache, one file per paper that has a DOI
    cache_dir = os.path.join(ROOT, "cache")
    doi_of = {pid: bg._norm_doi(p[3]) for pid, p in PAPERS.items()}
    for pid in PAPERS:
        refs = [{"DOI": doi_of[t]} for t in CITES.get(pid, [])]
        refs += [{"DOI": d} for d in NOISE]  # realistic extra refs, filtered out
        payload = {"message": {"DOI": doi_of[pid], "reference": refs}}
        cp = bg._cache_path(cache_dir, doi_of[pid])
        os.makedirs(os.path.dirname(cp), exist_ok=True)
        with open(cp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    print("Wrote sample/library.json (%d papers) and %d CrossRef cache files."
          % (len(csl), len(PAPERS)))


if __name__ == "__main__":
    main()
