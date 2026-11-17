"""Move references between the Zotero group libraries of this site.

Zotero has no move between libraries. For each item of the manifest, this
script copies the item (with its notes) into the target group, verifies the
copy, then sends the source item to the source group's trash. It never deletes.

usage: python scripts/zotero_move.py <manifest.json> plan|apply

  plan   reads only: checks every guard and prints what apply would write.
         Uses ZOTERO_API_KEY (read access is enough).
  apply  re-runs every guard, then writes. Needs "apply": true in the
         manifest. Uses ZOTERO_WRITE_API_KEY.

Every guard is fail-closed: any surprise stops the run before the next write.
"""
import json
import os
import sys
import uuid
from collections import Counter

import requests

BASE_URL = "https://api.zotero.org"

# slug -> environment variable holding the Zotero group ID
# (the same slugs as the pages built by generate_sota.py).
GROUP_ENV = {
    "p3579":       "ZOTERO_GROUP_ID_P3579",
    "p3998":       "ZOTERO_GROUP_ID_P3998",
    "p3579-p3998": "ZOTERO_GROUP_ID_P3579_P3998",
}

# Fields of the source item that are not copied: the server assigns them,
# or they point into the source library.
DROP_FIELDS = {
    "key", "version", "collections", "relations",
    "dateAdded", "dateModified", "deleted", "parentItem",
}

MOVE_FIELDS = ("source", "target", "key", "title", "to")


class MoveError(Exception):
    pass


# ── Zotero API ───────────────────────────────────────────────────────────────

def make_session(api_key):
    s = requests.Session()
    s.headers.update({"Zotero-API-Key": api_key, "Zotero-API-Version": "3"})
    return s


def get_json(s, path, params=None):
    r = s.get(f"{BASE_URL}{path}", params=params, timeout=30)
    if r.status_code != 200:
        raise MoveError(f"GET {path} -> {r.status_code} {r.text[:200]!r}")
    return r.json()


def get_item(s, gid, key):
    r = s.get(f"{BASE_URL}/groups/{gid}/items/{key}", timeout=30)
    if r.status_code == 404:
        raise MoveError(f"item {key} not found in group {gid}")
    if r.status_code != 200:
        raise MoveError(f"GET item {key} -> {r.status_code} {r.text[:200]!r}")
    return r.json()


def get_children(s, gid, key):
    children = get_json(s, f"/groups/{gid}/items/{key}/children", {"limit": 100})
    if len(children) >= 100:
        raise MoveError(f"item {key} has 100+ children: not handled")
    return children


def get_collections(s, gid):
    cols = get_json(s, f"/groups/{gid}/collections", {"limit": 100})
    if len(cols) >= 100:
        raise MoveError(f"group {gid} has 100+ collections: pagination not handled")
    return {c["data"]["key"]: c["data"] for c in cols}


def find_top_by_title(s, gid, title):
    """Top-level items of the group (trash excluded) whose title is exactly `title`."""
    items = get_json(
        s, f"/groups/{gid}/items/top",
        {"q": title, "qmode": "titleCreatorYear", "limit": 100},
    )
    return [i for i in items if i["data"].get("title") == title]


def post_items(s, gid, objects):
    """Create objects in one request; return their new keys, in order."""
    r = s.post(
        f"{BASE_URL}/groups/{gid}/items",
        json=objects,
        headers={"Zotero-Write-Token": uuid.uuid4().hex},
        timeout=30,
    )
    if r.status_code != 200:
        raise MoveError(f"POST items -> {r.status_code} {r.text[:200]!r}")
    body = r.json()
    # The docs name the success map both "successful" (index -> object)
    # and "success" (index -> key): accept either, require one.
    ok = body.get("successful") or body.get("success") or {}
    expected = {str(i) for i in range(len(objects))}
    if body.get("failed") or body.get("unchanged") or set(ok) != expected:
        raise MoveError(f"POST items: unexpected result {json.dumps(body)[:400]}")
    return [ok[str(i)]["key"] if isinstance(ok[str(i)], dict) else ok[str(i)]
            for i in range(len(objects))]


def send_to_trash(s, gid, key, version):
    r = s.patch(
        f"{BASE_URL}/groups/{gid}/items/{key}",
        json={"deleted": 1},
        headers={"If-Unmodified-Since-Version": str(version)},
        timeout=30,
    )
    if r.status_code != 204:
        raise MoveError(f"PATCH {key} deleted=1 -> {r.status_code} {r.text[:200]!r}")
    after = get_item(s, gid, key)["data"]
    if not after.get("deleted"):
        raise MoveError(f"PATCH {key} returned 204 but the item is not in the trash")


# ── Guards ───────────────────────────────────────────────────────────────────

def group_id(slug):
    env = GROUP_ENV.get(slug)
    if env is None:
        raise MoveError(f"unknown group slug {slug!r} (known: {', '.join(GROUP_ENV)})")
    value = os.environ.get(env, "")
    if not value:
        raise MoveError(f"{env} is missing or empty (set the repository secret)")
    return value


def check_move_fields(move):
    missing = [f for f in MOVE_FIELDS if not move.get(f)]
    if missing:
        raise MoveError(f"manifest entry {move!r}: missing {', '.join(missing)}")
    if not isinstance(move["to"], list) or not all(isinstance(p, str) for p in move["to"]):
        raise MoveError(f"manifest entry {move['key']}: 'to' must be a list of paths")
    if move["source"] == move["target"]:
        raise MoveError(f"manifest entry {move['key']}: source and target are the same group")


def collection_path(cols, key):
    names = []
    while key:
        col = cols[key]
        names.append(col["name"])
        key = col.get("parentCollection") or None
    return "/".join(reversed(names))


def resolve_targets(cols, paths):
    """Each path must name exactly one collection, and it must be a leaf
    (generate_sota.py does not publish references filed on a parent)."""
    by_path = {}
    for key in cols:
        by_path.setdefault(collection_path(cols, key), []).append(key)
    parents = {c.get("parentCollection") for c in cols.values() if c.get("parentCollection")}
    keys = []
    for path in paths:
        found = by_path.get(path, [])
        if len(found) != 1:
            raise MoveError(f"target collection {path!r}: {len(found)} match(es), expected 1")
        if found[0] in parents:
            raise MoveError(f"target collection {path!r} has sub-collections: "
                            "references filed on it are not published")
        keys.append(found[0])
    return keys


def verify_copy(s, gid, copy_key, src, want_cols, n_notes):
    copy = get_item(s, gid, copy_key)["data"]
    problems = [f for f in ("title", "itemType", "url", "creators")
                if copy.get(f) != src.get(f)]
    if sorted(copy.get("collections", [])) != sorted(want_cols):
        problems.append(f"collections {copy.get('collections')} != {want_cols}")
    if copy.get("deleted"):
        problems.append("the copy is in the trash")
    notes = [c for c in get_children(s, gid, copy_key) if c["data"]["itemType"] == "note"]
    if len(notes) != n_notes:
        problems.append(f"{len(notes)} note(s), expected {n_notes}")
    if problems:
        raise MoveError(f"copy {copy_key} does not match the source: {'; '.join(problems)}")


# ── Main ─────────────────────────────────────────────────────────────────────

def run(manifest_path, mode):
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    moves = manifest.get("moves") or []
    if mode == "apply" and manifest.get("apply") is not True:
        raise MoveError('apply mode needs "apply": true in the manifest')
    if not moves:
        print("No moves in the manifest: nothing to do.")
        return

    key_env = "ZOTERO_API_KEY" if mode == "plan" else "ZOTERO_WRITE_API_KEY"
    api_key = os.environ.get(key_env, "")
    if not api_key:
        raise MoveError(f"{key_env} is missing or empty (set the secret)")
    s = make_session(api_key)

    for move in moves:
        check_move_fields(move)
    cols_cache = {}

    # plan reports every item, then fails if any one is blocked;
    # apply stops at the first problem, before the next write.
    problems = []
    for n, move in enumerate(moves, 1):
        try:
            move_one(s, move, mode, cols_cache, n, len(moves))
        except MoveError as e:
            if mode == "apply":
                raise
            print(f"  BLOCKED: {e}")
            problems.append(f"{move['key']}: {e}")
    if problems:
        raise MoveError(f"plan: {len(problems)} item(s) blocked: " + " | ".join(problems))
    print(f"Done ({mode}).")


def move_one(s, move, mode, cols_cache, n, total):
    key, title = move["key"], move["title"]
    src_gid, dst_gid = group_id(move["source"]), group_id(move["target"])
    print(f"[{n}/{total}] {move['source']} {key} -> {move['target']} {move['to']}")

    if dst_gid not in cols_cache:
        cols_cache[dst_gid] = get_collections(s, dst_gid)
    target_keys = resolve_targets(cols_cache[dst_gid], move["to"])
    for path, col_key in zip(move["to"], target_keys):
        print(f"  target collection {path} -> {col_key} (leaf)")

    src = get_item(s, src_gid, key)
    d = src["data"]
    print(f"  source version {src['version']}, deleted={bool(d.get('deleted'))}, "
          f"itemType={d.get('itemType')}")
    if d.get("parentItem"):
        raise MoveError(f"{key} is a child item, not a top-level reference")
    if d.get("title") != title:
        raise MoveError(f"{key}: title {d.get('title')!r} != manifest {title!r}")

    children = get_children(s, src_gid, key)
    kinds = Counter(c["data"]["itemType"] for c in children)
    print(f"  children: {dict(kinds) if kinds else 'none'}")
    for c in children:
        cd = c["data"]
        if cd["itemType"] == "attachment":
            print(f"  attachment {cd.get('key')}: linkMode={cd.get('linkMode')}, "
                  f"contentType={cd.get('contentType')}, filename={cd.get('filename')!r}, "
                  f"title={cd.get('title')!r}, url={cd.get('url')!r}")
    if set(kinds) - {"note"}:
        raise MoveError(f"{key} has attachments ({dict(kinds)}): not handled")
    notes = [c["data"] for c in children if c["data"]["itemType"] == "note"]

    existing = find_top_by_title(s, dst_gid, title)
    if len(existing) > 1:
        raise MoveError(f"{len(existing)} items titled {title!r} in the target: resolve by hand")
    print(f"  already in target: {existing[0]['key'] if existing else 'no'}")

    # Source already in the trash: a verified copy means "already moved",
    # anything else stops. Either way nothing is written for this item.
    if d.get("deleted"):
        if not existing:
            raise MoveError(f"{key} is in the source trash and has no copy in the target")
        verify_copy(s, dst_gid, existing[0]["key"], d, target_keys, len(notes))
        print(f"  already moved (copy {existing[0]['key']} verified): skipped, nothing written")
        return

    payload = {k: v for k, v in d.items() if k not in DROP_FIELDS}
    payload["collections"] = target_keys
    note_payloads = [{"itemType": "note", "note": nd.get("note", ""),
                      "tags": nd.get("tags", [])} for nd in notes]
    if existing:
        print(f"  copy step: none (idempotent path, existing copy {existing[0]['key']} will be verified)")
    else:
        print(f"  copy step: POST item {json.dumps(payload, ensure_ascii=False)}")
        if note_payloads:
            print(f"  copy step: POST {len(note_payloads)} note(s) under the new item")
    print(f"  trash step: PATCH {key} deleted=1 (If-Unmodified-Since-Version {src['version']})")

    if mode == "plan":
        return

    if existing:
        copy_key = existing[0]["key"]
    else:
        copy_key = post_items(s, dst_gid, [payload])[0]
        print(f"  created {copy_key} in {move['target']}")
        if note_payloads:
            for np in note_payloads:
                np["parentItem"] = copy_key
            note_keys = post_items(s, dst_gid, note_payloads)
            print(f"  created notes {', '.join(note_keys)}")
    verify_copy(s, dst_gid, copy_key, d, target_keys, len(notes))
    print(f"  verified {copy_key}: title, itemType, url, creators, collections, notes")
    send_to_trash(s, src_gid, key, src["version"])
    print(f"  {key} sent to the {move['source']} trash (checked: deleted is set)")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in ("plan", "apply"):
        sys.exit("usage: python scripts/zotero_move.py <manifest.json> plan|apply")
    try:
        run(sys.argv[1], sys.argv[2])
    except MoveError as e:
        sys.exit(f"STOPPED: {e}")
