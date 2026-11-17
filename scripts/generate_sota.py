import requests, os, json, sys

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
        "References common to both IEEE P3579 and IEEE P3998. "
        "Project-specific references are listed on the "
        "[P3579](../p3579/index.md) and [P3998](../p3998/index.md) pages."
    ),
}

def get_all_collections(group_id):
    r = requests.get(
        f"{BASE_URL}/groups/{group_id}/collections",
        params={"limit": 100},
        headers=HEADERS
    )
    return {c["data"]["key"]: c["data"] for c in r.json()}

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
    r = requests.get(
        f"{BASE_URL}/groups/{group_id}/collections/{col_key}/items/top",
        params={"format": "json", "limit": 100},
        headers=HEADERS
    )
    return r.json()

def get_all_items(group_id):
    """Fetch all top-level items in the group (used for contributors list)."""
    r = requests.get(
        f"{BASE_URL}/groups/{group_id}/items/top",
        params={"format": "json", "limit": 100},
        headers=HEADERS
    )
    return r.json()

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

def get_notes(group_id, item_key):
    """Fetch notes attached to a reference."""
    r = requests.get(
        f"{BASE_URL}/groups/{group_id}/items/{item_key}/children",
        params={"itemType": "note"},
        headers=HEADERS
    )
    return r.json()

def clean_note(html_note):
    """Strip basic HTML tags from Zotero note content."""
    import re
    return re.sub(r'<[^>]+>', '', html_note).strip()

def render_table(group_id, items, published=None):
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
        authors  = ", ".join(
            a.get("lastName", "") for a in d.get("creators", [])
        ) or "—"
        title   = d.get("title", "—")
        url     = d.get("url", "")
        year    = str(d.get("date", "—"))[:4]
        doi     = d.get("DOI", "—")

        title_cell = f"[{title}]({url})" if url else title

        # Collect WG Notes for this item
        notes = get_notes(group_id, item_key)
        item_has_notes = False
        for note in notes:
            note_data = note.get("data", {})
            note_meta = note.get("meta", {})
            content   = clean_note(note_data.get("note", ""))
            creator   = note_meta.get("createdByUser", {}).get("username", "WG")
            date      = note_data.get("dateAdded", "")[:10]
            if content:
                all_notes.append((item_key, title, content, creator, date))
                item_has_notes = True

        # Build table row with anchor and optional note link
        note_cell = f'<a href="#note-{item_key}">📝</a>' if item_has_notes else "—"
        table_rows += f'| {authors} | <span id="ref-{item_key}">{title_cell}</span> | {year} | {doi} | {note_cell} |\n'

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
            output += f'<details id="note-{item_key}">\n'
            output += f'<summary>💬 <b>{ref_title}</b> — {summary}</summary>\n\n'
            output += f'<p>{content}</p>\n'
            output += f'<p><em>— {creator}, {date}</em> · <a href="#ref-{item_key}">↩ back to reference</a></p>\n\n'
            output += f'</details>\n\n'

    return output

def render_section(group_id, col_key, collections, children, depth=2, published=None):
    col     = collections[col_key]
    name    = col["name"]
    heading = "#" * depth
    output  = f"{heading} {name}\n\n"

    sub_keys = children.get(col_key, [])

    if sub_keys:
        for sub_key in sub_keys:
            output += render_section(
                group_id, sub_key, collections, children, depth + 1, published
            )
    else:
        items = get_items(group_id, col_key)
        output += render_table(group_id, items, published)

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
    Any edit in Zotero (a field, a tag, a collection) counts as a modification."""
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
latest_blocks = {}
for wg, (group_id, label) in GROUPS.items():
    output = f"# State of the Art — {label}\n\n"
    intro = INTROS.get(wg)
    if intro:
        output += f"{intro}\n\n"

    collections     = get_all_collections(group_id)
    roots, children = build_hierarchy(collections)

    published = {}
    for root_key in roots:
        output += render_section(group_id, root_key, collections, children, published=published)
    latest_blocks[wg] = render_latest(wg, published)

    # Contributors section
    all_items    = get_all_items(group_id)
    contributors = get_contributors(all_items)
    if contributors:
        output += "\n---\n\n## Contributors\n\n"
        output += "*The following members have contributed references to this library:*\n\n"
        for c in contributors:
            output += f"- [{c}](https://www.zotero.org/{c})\n"
        output += "\n"

    os.makedirs(f"docs/{wg}", exist_ok=True)
    with open(f"docs/{wg}/index.md", "w") as f:
        f.write(output)
    print(f"Generated docs/{wg}/index.md")

update_home(latest_blocks)
