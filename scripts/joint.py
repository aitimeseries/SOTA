"""Pure functions for the joint page (issue #18): which references are common
to IEEE P3579 and IEEE P3998, and where they go on the page.

No network and no environment here, so that scripts/check_matching.py can
exercise every rule offline, at every sync, before the pages are generated.
"""
from collections import Counter
from urllib.parse import urlsplit, urlunsplit

# Item types that are not references.
NON_REFERENCE_TYPES = {"note", "attachment", "annotation"}

DOI_PREFIXES = (
    "https://doi.org/", "http://doi.org/",
    "https://dx.doi.org/", "http://dx.doi.org/",
    "doi:",
)

# Fields compared between two matched copies (a difference is reported).
DIVERGENCE_FIELDS = ("title", "date", "creators")


def is_reference(data):
    return data.get("itemType") not in NON_REFERENCE_TYPES


def normalize_doi(value):
    """Lower case, without a doi.org / dx.doi.org / doi: prefix; None if empty."""
    doi = (value or "").strip().lower()
    for prefix in DOI_PREFIXES:
        if doi.startswith(prefix):
            doi = doi[len(prefix):].strip()
            break
    return doi or None


def normalize_url(value):
    """Trimmed, scheme and host lower-cased, no trailing '/'; None if empty."""
    url = (value or "").strip()
    if not url:
        return None
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                       parts.path.rstrip("/"), parts.query, parts.fragment))


def item_uri(group_id, key):
    """The URI Zotero writes in relations for a group item."""
    return f"http://zotero.org/groups/{group_id}/items/{key}"


def same_as(data):
    """The owl:sameAs relations of an item, as a set (one URI or a list)."""
    value = (data.get("relations") or {}).get("owl:sameAs")
    if not value:
        return set()
    if isinstance(value, str):
        return {value}
    return {v for v in value if isinstance(v, str)}


def match_rule(a_gid, a, b_gid, b):
    """How two items are the same reference, or None.

    1. owl:sameAs, in either direction, or both naming a third item;
    2. else, when both have a DOI: the same normalized DOI (two different
       DOIs mean no match, even with the same URL);
    3. else, the same normalized non-empty URL.
    Empty values never match.
    """
    ids_a = {item_uri(a_gid, a.get("key"))} | same_as(a)
    ids_b = {item_uri(b_gid, b.get("key"))} | same_as(b)
    if ids_a & ids_b:
        return "owl:sameAs"
    doi_a, doi_b = normalize_doi(a.get("DOI")), normalize_doi(b.get("DOI"))
    if doi_a and doi_b:
        return "DOI" if doi_a == doi_b else None
    url_a, url_b = normalize_url(a.get("url")), normalize_url(b.get("url"))
    if url_a and url_b and url_a == url_b:
        return "URL"
    return None


def find_common(a_gid, a_items, b_gid, b_items):
    """a_items, b_items: {key: data} of the published items of each group.

    Returns (pairs, ambiguous): pairs is a sorted list of (a_key, b_key, rule)
    matched one to one; ambiguous lists the candidate (a_key, b_key, rule)
    involving an item that matches more than one item of the other group.
    Those are not common: the sync names them and picks none.
    """
    a_refs = {k: d for k, d in a_items.items() if is_reference(d)}
    b_refs = {k: d for k, d in b_items.items() if is_reference(d)}
    candidates = []
    for a_key, a in a_refs.items():
        for b_key, b in b_refs.items():
            rule = match_rule(a_gid, a, b_gid, b)
            if rule:
                candidates.append((a_key, b_key, rule))
    a_count = Counter(a_key for a_key, _, _ in candidates)
    b_count = Counter(b_key for _, b_key, _ in candidates)
    pairs, ambiguous = [], []
    for a_key, b_key, rule in candidates:
        if a_count[a_key] == 1 and b_count[b_key] == 1:
            pairs.append((a_key, b_key, rule))
        else:
            ambiguous.append((a_key, b_key, rule))
    return sorted(pairs), sorted(ambiguous)


def divergences(a, b):
    """The fields on which two matched copies differ."""
    return [f for f in DIVERGENCE_FIELDS if a.get(f) != b.get(f)]


def collection_path(collections, key):
    """The name path of a collection, e.g. ('RESOURCES', 'Models')."""
    names = []
    while key:
        col = collections[key]
        names.append(col["name"])
        key = col.get("parentCollection") or None
    return tuple(reversed(names))


def leaf_paths(item_collections, collections, children):
    """Name paths of the item's collections that have no sub-collection."""
    return [collection_path(collections, key)
            for key in item_collections
            if key in collections and key not in children]


def fold(path):
    return tuple(name.casefold() for name in path)


def joint_paths(paths_a, paths_b):
    """Union of both copies' paths, compared casefolded. When one path is a
    prefix of another, only the deeper one is kept."""
    by_fold = {}
    for path in list(paths_a) + list(paths_b):
        by_fold.setdefault(fold(path), path)
    folds = list(by_fold)
    kept = [f for f in folds
            if not any(o != f and o[:len(f)] == f for o in folds)]
    return sorted((by_fold[f] for f in kept), key=fold)


def build_tree(placements):
    """placements: (path, key) pairs. A node is {name, children, items}."""
    root = {"name": None, "children": {}, "items": []}
    for path, key in placements:
        node = root
        for name in path:
            node = node["children"].setdefault(
                name.casefold(), {"name": name, "children": {}, "items": []})
        if key not in node["items"]:
            node["items"].append(key)
    return root


def non_leaf_holders(node, path=()):
    """Paths of the tree's nodes that hold items and also have sub-nodes."""
    found = []
    for child in node["children"].values():
        child_path = path + (child["name"],)
        if child["items"] and child["children"]:
            found.append(child_path)
        found.extend(non_leaf_holders(child, child_path))
    return found


def unpublished(all_items, collections, children):
    """References filed in no collection without sub-collections, as
    (key, title, where): they are on no page."""
    leaves = {key for key in collections if key not in children}
    found = []
    for item in all_items:
        data = item.get("data", {})
        if not is_reference(data):
            continue
        filed = data.get("collections", [])
        if not leaves.intersection(filed):
            where = "no section" if not filed else "a section with sub-sections"
            found.append((data.get("key"), data.get("title", "?"), where))
    return found


def dedupe_notes(notes):
    """Notes of both copies, each text once (a drag copies the notes)."""
    seen, kept = set(), []
    for note in notes:
        text = note.get("data", {}).get("note", "").strip()
        if text in seen:
            continue
        seen.add(text)
        kept.append(note)
    return kept
