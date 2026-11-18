"""Offline check of the joint-page rules in scripts/joint.py (C-S19-1).

Runs before the sync generates any page: a failing rule stops the run, so a
matching bug never publishes. Fixtures are item `data` dicts shaped like the
Zotero API's. Each rule has a positive and a negative case.

usage: python scripts/check_matching.py
"""
import sys

import joint

A, B, C = "111", "222", "333"          # group ids (fixtures, not real groups)
failures = []


def check(name, condition):
    print(f"{'ok  ' if condition else 'FAIL'} {name}")
    if not condition:
        failures.append(name)


def item(key, **fields):
    data = {"key": key, "itemType": "journalArticle", "title": key,
            "DOI": "", "url": "", "relations": {}, "collections": []}
    data.update(fields)
    return data


# ── Normalization ───────────────────────────────────────────────────────────
check("doi: https://doi.org/ prefix and case",
      joint.normalize_doi("https://doi.org/10.1109/ACCESS.2020.2981488")
      == "10.1109/access.2020.2981488")
check("doi: http://dx.doi.org/ and doi: prefixes",
      joint.normalize_doi("http://dx.doi.org/10.1/X")
      == joint.normalize_doi("DOI:10.1/x") == "10.1/x")
check("doi: empty or blank is None",
      joint.normalize_doi("") is None and joint.normalize_doi("  ") is None
      and joint.normalize_doi(None) is None)
check("url: scheme and host case, trailing slash",
      joint.normalize_url("HTTPS://HuggingFace.co/models/")
      == joint.normalize_url("https://huggingface.co/models"))
check("url: path case and query are kept",
      joint.normalize_url("https://x.org/A?q=1") != joint.normalize_url("https://x.org/a?q=1")
      and joint.normalize_url("https://x.org/a?q=1") != joint.normalize_url("https://x.org/a"))
check("url: empty or blank is None",
      joint.normalize_url("") is None and joint.normalize_url(" ") is None)

# ── Matching rules ──────────────────────────────────────────────────────────
a1 = item("A1")
b1 = item("B1", relations={"owl:sameAs": joint.item_uri(A, "A1")})
check("link: one URI, B copy names A", joint.match_rule(A, a1, B, b1) == "owl:sameAs")
check("link: read in the other direction too", joint.match_rule(B, b1, A, a1) == "owl:sameAs")

a2 = item("A2", relations={"owl:sameAs": [joint.item_uri(C, "X"), joint.item_uri(B, "B2")]})
b2 = item("B2")
check("link: a list of URIs", joint.match_rule(A, a2, B, b2) == "owl:sameAs")

a3 = item("A3", relations={"owl:sameAs": joint.item_uri(C, "X3")})
b3 = item("B3", relations={"owl:sameAs": [joint.item_uri(C, "X3")]})
check("link: both copies name a third item", joint.match_rule(A, a3, B, b3) == "owl:sameAs")
check("link: naming an unrelated item is no match",
      joint.match_rule(A, item("A9", relations={"owl:sameAs": joint.item_uri(C, "Z")}),
                       B, item("B9")) is None)

check("doi: same DOI, different forms",
      joint.match_rule(A, item("A4", DOI="10.1109/ACCESS.2020.2981488"),
                       B, item("B4", DOI="https://doi.org/10.1109/access.2020.2981488")) == "DOI")
check("doi: two different DOIs with the same URL is no match",
      joint.match_rule(A, item("A5", DOI="10.1/a", url="https://x.org/p"),
                       B, item("B5", DOI="10.1/b", url="https://x.org/p")) is None)
check("url: same URL, one DOI missing",
      joint.match_rule(A, item("A6", DOI="10.1/a", url="https://x.org/p/"),
                       B, item("B6", url="HTTPS://X.org/p")) == "URL")
check("url: different URLs, no DOI, is no match",
      joint.match_rule(A, item("A7", url="https://x.org/p"),
                       B, item("B7", url="https://x.org/q")) is None)
check("empty: empty DOI and empty URL never match",
      joint.match_rule(A, item("A8"), B, item("B8")) is None)

# Today's data: four web pages with DOI "" (P-S18-3) must not match.
hf_models = item("UGU54QGJ", itemType="webpage", url="https://huggingface.co/models")
chronos = item("6CB8RX6D", itemType="webpage",
               url="https://huggingface.co/collections/amazon/chronos-models-and-datasets")
a2c = item("Z6TDV2T2", itemType="webpage",
           url="https://stable-baselines3.readthedocs.io/en/master/modules/a2c.html"
               "#stable_baselines3.a2c.A2C.logger")
ppo = item("FCNVJ24Q", itemType="webpage",
           url="https://stable-baselines3.readthedocs.io/en/master/common/logger.html")
pairs, ambiguous = joint.find_common(A, {"UGU54QGJ": hf_models, "6CB8RX6D": chronos},
                                     B, {"Z6TDV2T2": a2c, "FCNVJ24Q": ppo})
check("today: the four empty-DOI web pages give no pair and no ambiguity",
      pairs == [] and ambiguous == [])

# ── One to one, regular items only ──────────────────────────────────────────
pairs, ambiguous = joint.find_common(
    A, {"A1": a1}, B, {"B1": b1, "N1": item("N1", itemType="note", url="")})
check("one to one: a single match is a pair", pairs == [("A1", "B1", "owl:sameAs")] and not ambiguous)

pairs, ambiguous = joint.find_common(
    A, {"A10": item("A10", itemType="webpage", url="https://x.org/r")},
    B, {"T10": item("T10", itemType="attachment", url="https://x.org/r")})
check("regular items only: an attachment with the same URL is no match", pairs == [] and ambiguous == [])

pairs, ambiguous = joint.find_common(
    A, {"A11": item("A11", url="https://x.org/s")},
    B, {"B11": item("B11", url="https://x.org/s"), "C11": item("C11", url="https://x.org/s/")})
check("ambiguity: one item matching two gives no pair", pairs == [] and len(ambiguous) == 2)

# ── Divergence ──────────────────────────────────────────────────────────────
check("divergence: a title edited in one copy only",
      joint.divergences(item("A12", title="T"), item("B12", title="T (2nd ed.)")) == ["title"])
check("divergence: identical copies",
      joint.divergences(item("A13", title="T"), item("A13", title="T")) == [])

# ── Sections of the joint page ──────────────────────────────────────────────
cols = {
    "P": {"name": "PUBLICATIONS", "parentCollection": False},
    "PP": {"name": "Papers", "parentCollection": "P"},
    "R": {"name": "RESOURCES", "parentCollection": False},
    "RM": {"name": "Models", "parentCollection": "R"},
}
children = {"P": ["PP"], "R": ["RM"]}
check("leaf paths: only collections without sub-collections",
      joint.leaf_paths(["P", "PP", "RM"], cols, children)
      == [("PUBLICATIONS", "Papers"), ("RESOURCES", "Models")])
check("joint paths: casefolded union, deeper path kept",
      joint.joint_paths([("PUBLICATIONS",), ("RESOURCES", "Models")],
                        [("Publications", "Papers"), ("resources", "models")])
      == [("Publications", "Papers"), ("RESOURCES", "Models")])
check("joint paths: unrelated paths both kept",
      joint.joint_paths([("RESOURCES", "Models")], [("RESOURCES", "Datasets")])
      == [("RESOURCES", "Datasets"), ("RESOURCES", "Models")])

tree = joint.build_tree([(("PUBLICATIONS",), "k1"), (("PUBLICATIONS", "Papers"), "k2"),
                         (("RESOURCES", "Models"), "k3")])
check("tree: a node holding items and sub-nodes is reported",
      joint.non_leaf_holders(tree) == [("PUBLICATIONS",)])
tree = joint.build_tree([(("RESOURCES", "Models"), "k3"), (("RESOURCES", "Models"), "k3")])
check("tree: no hole, and an item placed twice on one path appears once",
      joint.non_leaf_holders(tree) == []
      and tree["children"]["resources"]["children"]["models"]["items"] == ["k3"])

# ── Unpublished-item guard ──────────────────────────────────────────────────
found = joint.unpublished(
    [{"data": item("U1", collections=["P"])},          # on a parent only
     {"data": item("U2", collections=[])},             # unfiled
     {"data": item("U3", collections=["P", "PP"])},    # on a leaf too
     {"data": item("U4", itemType="note")}],           # not a reference
    cols, children)
check("guard: parent-only and unfiled references are named, the others are not",
      [(k, w) for k, _, w in found]
      == [("U1", "a section with sub-sections"), ("U2", "no section")])

# ── Notes ───────────────────────────────────────────────────────────────────
notes = [{"data": {"note": "<p>WG note</p>"}}, {"data": {"note": "<p>WG note</p> "}},
         {"data": {"note": "<p>Other</p>"}}]
check("notes: a note copied by the drag shows once", len(joint.dedupe_notes(notes)) == 2)

if failures:
    sys.exit(f"{len(failures)} check(s) failed: {', '.join(failures)}")
print("All matching checks passed.")
