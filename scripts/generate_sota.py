import requests, os, json, sys

import joint   # scripts/joint.py: the joint-page rules, checked offline by check_matching.py

# slug -> (environment variable holding the Zotero group ID, page label).
# The slug is the docs/ folder and the URL path of the page.
GROUP_ENV = {
    "p3579":       ("ZOTERO_GROUP_ID_P3579",       "IEEE P3579"),
    "p3998":       ("ZOTERO_GROUP_ID_P3998",       "IEEE P3998"),
    "p3579-p3998": ("ZOTERO_GROUP_ID_P3579_P3998", "IEEE P3579 & P3998 (Joint)"),
}

# In a workflow, an unset secret is an empty string, not a missing variable:
# fail early and name the secret, instead of a JSONDecodeError on Zotero's
# text/html error page.
REQUIRED_ENV = ["ZOTERO_API_KEY"] + [env for env, _ in GROUP_ENV.values()]
missing = [env for env in REQUIRED_ENV if not os.environ.get(env)]
if missing:
    sys.exit(f"Missing or empty: {', '.join(missing)} (set the repository secret)")

API_KEY  = os.environ["ZOTERO_API_KEY"]
HEADERS  = {"Zotero-API-Key": API_KEY}
BASE_URL = "https://api.zotero.org"

GROUPS = {
    slug: (os.environ[env], label) for slug, (env, label) in GROUP_ENV.items()
}

# The two project groups are read and rendered; the joint page is computed
# from them (#18): a reference is common when it is in both.
PROJECTS = ("p3579", "p3998")
JOINT    = "p3579-p3998"

# Intro line under each page title. The pages are regenerated at each sync:
# edit the text here, never in docs/.
JOINT_LINK = (
    "*See also the [references common to P3579 and P3998]"
    "(../p3579-p3998/index.md).*"
)
INTROS = {
    "p3579": JOINT_LINK,
    "p3998": JOINT_LINK,
    "p3579-p3998": (
        "References that are in both IEEE P3579 and IEEE P3998, computed by "
        "the sync; they also appear on each project's page "
        "([P3579](../p3579/index.md), [P3998](../p3998/index.md))."
    ),
}

class LibraryMoved(Exception):
    pass

def get_paged(path, params=None):
    """Every result of a Zotero list endpoint, page by page (100 per page).
    If the library changes during the read, the read starts over once; a
    second change stops the run (C-S19-3: members may edit during a sync)."""
    try:
        return _read_pages(path, params)
    except LibraryMoved as moved:
        print(f"GET {path}: {moved}; reading again")
        try:
            return _read_pages(path, params)
        except LibraryMoved as moved_again:
            sys.exit(f"GET {path}: {moved_again} twice in a row; run the sync again")

def _read_pages(path, params):
    """One complete read. Stops the run on an HTTP error, a missing
    Total-Results header, or when the number of distinct keys read differs
    from Total-Results: a truncated read must never pass for a full one."""
    params = dict(params or {}, limit=100)
    results, start, total, version = [], 0, None, None
    while True:
        r = requests.get(
            f"{BASE_URL}{path}",
            params=dict(params, start=start),
            headers=HEADERS,
            timeout=30,
        )
        if r.status_code != 200:
            sys.exit(f"GET {path} -> {r.status_code} {r.text[:200]!r}")
        if "Total-Results" not in r.headers:
            sys.exit(f"GET {path}: no Total-Results header, cannot check the read is complete")
        # Last-Modified-Version is the library version: if it moves between two
        # pages, an item was added, edited or deleted mid-read and the pages may
        # have shifted (a deletion can skip an item with every count still right).
        if "Last-Modified-Version" not in r.headers:
            sys.exit(f"GET {path}: no Last-Modified-Version header, cannot check the read is consistent")
        page_version = r.headers["Last-Modified-Version"]
        if version is None:
            version = page_version
        elif page_version != version:
            raise LibraryMoved(f"the library changed during the read "
                               f"(version {version} -> {page_version})")
        page = r.json()
        results.extend(page)
        total = int(r.headers["Total-Results"])
        start += len(page)
        if not page or start >= total:
            break
    keys = {res.get("key") or res.get("data", {}).get("key") for res in results}
    if len(results) != total or len(keys) != total:
        sys.exit(f"GET {path}: read {len(results)} results ({len(keys)} distinct), "
                 f"Total-Results says {total}")
    return results

def annotation(text):
    """Escape a message for a GitHub Actions workflow command."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")

def get_all_collections(group_id):
    cols = get_paged(f"/groups/{group_id}/collections")
    return {c["data"]["key"]: c["data"] for c in cols}

def build_hierarchy(collections):
    children = {}
    roots = []
    for key, col in collections.items():
        parent = col.get("parentCollection", False)
        if not parent:
            roots.append(key)
        else:
            children.setdefault(parent, []).append(key)

    # Sections in alphabetical order at every level (the API order is not).
    def by_name(key):
        return collections[key]["name"].casefold()

    roots.sort(key=by_name)
    for sub_keys in children.values():
        sub_keys.sort(key=by_name)
    return roots, children

def get_items(group_id, col_key):
    return get_paged(
        f"/groups/{group_id}/collections/{col_key}/items/top", {"format": "json"}
    )

def get_all_items(group_id):
    """Fetch all top-level items in the group (used for contributors list)."""
    return get_paged(f"/groups/{group_id}/items/top", {"format": "json"})

def warn_unpublished(wg, all_items, collections, children):
    """A reference that sits in no section without sub-sections is on no page:
    name it in a GitHub Actions annotation (the run stays green)."""
    for key, title, where in joint.unpublished(all_items, collections, children):
        message = (f"{wg}: '{title}' ({key}) is on no page: "
                   f"it is filed in {where}, not in a section without sub-sections")
        print(f"::warning::{annotation(message)}")

def get_contributors(items):
    """Extract unique contributor usernames.

    Zotero places createdByUser in item['meta'], not item['data'].
    Falls back to 'addedBy' and 'name' if 'username' is absent.
    """
    contributors = set()
    for item in items:
        meta = item.get("meta", {})
        user = meta.get("createdByUser", {})
        if isinstance(user, dict):
            # Try username first, then name
            name = user.get("username") or user.get("name", "")
            if name:
                contributors.add(name)
    return sorted(contributors)

NOTES_CACHE = {}

def get_notes(group_id, item_key):
    """Fetch notes attached to a reference (read once per run: the joint page
    reuses the notes read for the project pages)."""
    if (group_id, item_key) not in NOTES_CACHE:
        NOTES_CACHE[(group_id, item_key)] = get_paged(
            f"/groups/{group_id}/items/{item_key}/children", {"itemType": "note"}
        )
    return NOTES_CACHE[(group_id, item_key)]

def clean_note(html_note):
    """Strip basic HTML tags from Zotero note content."""
    import re
    return re.sub(r'<[^>]+>', '', html_note).strip()

def render_table(group_id, items, published=None, page_ids=None, notes_lookup=None):
    """page_ids: the ids already emitted on this page. A reference filed in
    several sections keeps a row in each, but its ref- id and its note blocks
    (with their note- ids) are emitted at its first occurrence only.
    notes_lookup(key), when given, replaces get_notes(group_id, key)."""
    page_ids = set() if page_ids is None else page_ids
    if not items:
        return "_No references yet._\n\n"

    items = sorted(
        items,
        key=lambda i: str(i.get("data", {}).get("date", "0"))[:4],
        reverse=True,
    )

    table_rows = ""
    all_notes  = []

    for item in items:
        d        = item.get("data", {})
        item_key = item["data"]["key"]
        if published is not None:
            published[item_key] = item
        ref_id = f"ref-{item_key}"
        first  = ref_id not in page_ids
        page_ids.add(ref_id)
        authors  = ", ".join(
            a.get("lastName", "") for a in d.get("creators", [])
        ) or "—"
        title   = d.get("title", "—")
        url     = d.get("url", "")
        year    = str(d.get("date", "—"))[:4]
        doi     = d.get("DOI", "—")

        title_cell = f"[{title}]({url})" if url else title

        # Collect WG Notes for this item
        notes = notes_lookup(item_key) if notes_lookup else get_notes(group_id, item_key)
        item_has_notes = False
        for note in notes:
            note_data = note.get("data", {})
            note_meta = note.get("meta", {})
            content   = clean_note(note_data.get("note", ""))
            creator   = note_meta.get("createdByUser", {}).get("username", "WG")
            date      = note_data.get("dateAdded", "")[:10]
            if content:
                if first:
                    all_notes.append((item_key, title, content, creator, date))
                item_has_notes = True

        # Build table row with anchor (first occurrence only) and optional note link
        note_cell = f'<a href="#note-{item_key}">📝</a>' if item_has_notes else "—"
        span_open = f'<span id="{ref_id}">' if first else "<span>"
        table_rows += f'| {authors} | {span_open}{title_cell}</span> | {year} | {doi} | {note_cell} |\n'

    # Output: table first
    output  = "| Authors | Title | Year | DOI | Notes |\n"
    output += "|---------|-------|------|-----|-------|\n"
    output += table_rows + "\n"

    # Render notes after the table with back-links
    if all_notes:
        for item_key, ref_title, content, creator, date in all_notes:
            if len(content) > 80:
                summary = content[:80].rsplit(" ", 1)[0] + "…"
            else:
                summary = content
            note_id = f"note-{item_key}"
            id_attr = f' id="{note_id}"' if note_id not in page_ids else ""
            page_ids.add(note_id)
            output += f'<details{id_attr}>\n'
            output += f'<summary>💬 <b>{ref_title}</b> — {summary}</summary>\n\n'
            output += f'<p>{content}</p>\n'
            output += f'<p><em>— {creator}, {date}</em> · <a href="#ref-{item_key}">↩ back to reference</a></p>\n\n'
            output += f'</details>\n\n'

    return output

def render_section(group_id, col_key, collections, children, depth=2,
                   published=None, page_ids=None):
    col     = collections[col_key]
    name    = col["name"]
    heading = "#" * depth
    output  = f"{heading} {name}\n\n"

    sub_keys = children.get(col_key, [])

    if sub_keys:
        for sub_key in sub_keys:
            output += render_section(
                group_id, sub_key, collections, children, depth + 1,
                published, page_ids
            )
    else:
        items = get_items(group_id, col_key)
        output += render_table(group_id, items, published, page_ids)

    return output

# ── Latest updates on the home page ─────────────────────────────────────────
LATEST_COUNT = 5     # references per project on the home page
TITLE_MAX    = 60    # characters per title on the home page, "…" included

def shorten(title, limit=TITLE_MAX):
    """Cut a title to `limit` characters at a word boundary, ending with "…"."""
    if len(title) <= limit:
        return title
    head = title[:limit]
    if " " in head:
        # The last space within the first `limit` characters: the words
        # before it fit in limit - 1 characters, leaving room for "…".
        cut = head[:head.rfind(" ")]
    else:
        cut = title[:limit - 1]
    return cut.rstrip(" ,;:.-–—") + "…"

def render_latest(wg, published):
    """The LATEST_COUNT most recently modified references published on the
    page of `wg` (all sections together), as a table for the home page.
    An edit of a field or a tag counts as a modification; a change of
    collection alone does not, from any client (Zotero skips the dateModified
    update)."""
    items = sorted(
        published.values(),
        key=lambda i: i.get("data", {}).get("dateModified", ""),
        reverse=True,
    )[:LATEST_COUNT]
    if not items:
        return "_No references yet._\n"
    output  = "**Latest updates**\n\n"
    output += "| Updated | Reference | Contributor |\n"
    output += "|---------|-----------|-------------|\n"
    for item in items:
        d     = item.get("data", {})
        meta  = item.get("meta", {})
        title = d.get("title") or "—"
        text  = shorten(title).replace("[", "(").replace("]", ")").replace("|", "\\|")
        hover = title.replace('"', "'").replace("|", "\\|")
        # Who made the last change; Zotero reports it for group items, and the
        # creator stands in when it does not.
        user  = meta.get("lastModifiedByUser") or meta.get("createdByUser") or {}
        name  = user.get("username") or user.get("name", "") if isinstance(user, dict) else ""
        who   = f"[{name}](https://www.zotero.org/{name})" if name else "—"
        when  = d.get("dateModified", "")[:10] or "—"
        output += f'| {when} | [{text}]({wg}/index.md#ref-{d["key"]} "{hover}") | {who} |\n'
    return output

def update_home(blocks, path="docs/index.md"):
    """Replace what sits between <!-- latest:<wg> --> and <!-- /latest:<wg> -->
    in the home page. A page without the markers is left as it is."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    updated, skipped = [], []
    for wg, block in blocks.items():
        start, end = f"<!-- latest:{wg} -->", f"<!-- /latest:{wg} -->"
        if text.count(start) != 1 or text.count(end) != 1 or text.index(start) > text.index(end):
            # A GitHub Actions annotation: shown on the run page, the run stays
            # green so the project pages still get their weekly update.
            print(f"::warning file={path}::no single {start} ... {end} pair: "
                  f"the {wg} latest-updates block was not updated")
            skipped.append(wg)
            continue
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        # Blank lines around the block: an HTML comment line would otherwise
        # swallow the Markdown right after it.
        text = before + start + "\n\n" + block.rstrip("\n") + "\n\n" + end + after
        updated.append(wg)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Updated {path} (latest updates: {', '.join(updated) or 'none'}"
          f"{'; NOT updated: ' + ', '.join(skipped) if skipped else ''})")

# ── Main ─────────────────────────────────────────────────────────────────────
def username(item):
    user = item.get("meta", {}).get("createdByUser", {})
    if not isinstance(user, dict):
        return ""
    return user.get("username") or user.get("name", "")

def contributors_section(names):
    if not names:
        return ""
    output  = "\n---\n\n## Contributors\n\n"
    output += "*The following members have contributed references to this library:*\n\n"
    for c in sorted(names):
        output += f"- [{c}](https://www.zotero.org/{c})\n"
    return output + "\n"

def render_joint_node(node, items, notes_by_key, depth, published, page_ids):
    """Sections of the joint page, from the tree of common items' paths,
    in alphabetical order. Items at a node that also has sub-sections are
    rendered there, with a warning, never dropped."""
    output = ""
    for name_fold in sorted(node["children"]):
        child = node["children"][name_fold]
        output += f"{'#' * depth} {child['name']}\n\n"
        if child["items"]:
            output += render_table(
                None, [items[key] for key in child["items"]], published, page_ids,
                notes_lookup=lambda key: notes_by_key.get(key, []))
        output += render_joint_node(child, items, notes_by_key, depth + 1,
                                    published, page_ids)
    return output

def render_joint(state):
    """The joint page: the references present in both project groups."""
    a, b = state["p3579"], state["p3998"]
    a_data = {k: item["data"] for k, item in a["published"].items()}
    b_data = {k: item["data"] for k, item in b["published"].items()}
    pairs, ambiguous = joint.find_common(a["gid"], a_data, b["gid"], b_data)

    for a_key, b_key, rule in ambiguous:
        message = (f"{JOINT}: p3579 {a_key} and p3998 {b_key} match by {rule}, but one of them "
                   f"matches another item too: not shown as common, resolve by hand")
        print(f"::warning::{annotation(message)}")

    items, notes_by_key, placements, names = {}, {}, [], set()
    for a_key, b_key, rule in pairs:
        item_a, item_b = a["published"][a_key], b["published"][b_key]
        print(f"{JOINT}: p3579 {a_key} <-> p3998 {b_key} by {rule}; "
              f"owl:sameAs p3579={item_a['data'].get('relations', {}).get('owl:sameAs')!r} "
              f"p3998={item_b['data'].get('relations', {}).get('owl:sameAs')!r}")
        diff = joint.divergences(item_a["data"], item_b["data"])
        if diff:
            message = (f"{JOINT}: the copies p3579 {a_key} and p3998 {b_key} differ on "
                       f"{', '.join(diff)}: the most recently modified one is shown")
            print(f"::warning::{annotation(message)}")
        # Fields from the most recently modified copy; the anchor stays on the
        # P3579 key, so deep links and the home link do not move (C-S18-3).
        shown = max((item_a, item_b), key=lambda it: it["data"].get("dateModified", ""))
        items[a_key] = {"data": dict(shown["data"], key=a_key), "meta": shown.get("meta", {})}
        notes_by_key[a_key] = joint.dedupe_notes(
            get_notes(a["gid"], a_key) + get_notes(b["gid"], b_key))
        paths = joint.joint_paths(
            joint.leaf_paths(item_a["data"].get("collections", []), a["collections"], a["children"]),
            joint.leaf_paths(item_b["data"].get("collections", []), b["collections"], b["children"]))
        placements += [(path, a_key) for path in paths]
        names.update(n for n in (username(item_a), username(item_b)) if n)

    output  = f"# State of the Art — {GROUP_ENV[JOINT][1]}\n\n{INTROS[JOINT]}\n\n"
    published = {}
    if not items:
        output += "_No references yet._\n\n"
    else:
        tree = joint.build_tree(placements)
        for path in joint.non_leaf_holders(tree):
            message = (f"{JOINT}: section '{'/'.join(path)}' holds common references and has "
                       f"sub-sections in the joint tree: align the two project trees")
            print(f"::warning::{annotation(message)}")
        output += render_joint_node(tree, items, notes_by_key, 2, published, set())
        output += contributors_section(names)

    os.makedirs(f"docs/{JOINT}", exist_ok=True)
    with open(f"docs/{JOINT}/index.md", "w") as f:
        f.write(output)
    print(f"Generated docs/{JOINT}/index.md ({len(items)} common reference(s))")
    return render_latest(JOINT, published)

latest_blocks = {}
state = {}
for wg in PROJECTS:
    group_id, label = GROUPS[wg]
    output = f"# State of the Art — {label}\n\n"
    intro = INTROS.get(wg)
    if intro:
        output += f"{intro}\n\n"

    collections     = get_all_collections(group_id)
    roots, children = build_hierarchy(collections)

    published = {}
    page_ids  = set()    # ids emitted on this page (one set per page, P-S19-15)
    for root_key in roots:
        output += render_section(group_id, root_key, collections, children,
                                 published=published, page_ids=page_ids)
    latest_blocks[wg] = render_latest(wg, published)

    # Contributors section
    all_items    = get_all_items(group_id)
    warn_unpublished(wg, all_items, collections, children)
    output += contributors_section(get_contributors(all_items))

    os.makedirs(f"docs/{wg}", exist_ok=True)
    with open(f"docs/{wg}/index.md", "w") as f:
        f.write(output)
    print(f"Generated docs/{wg}/index.md")

    state[wg] = {"gid": group_id, "collections": collections,
                 "children": children, "published": published}

latest_blocks[JOINT] = render_joint(state)
update_home(latest_blocks)
