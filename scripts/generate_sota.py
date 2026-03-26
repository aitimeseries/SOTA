import requests, os, json

API_KEY  = os.environ["ZOTERO_API_KEY"]
HEADERS  = {"Zotero-API-Key": API_KEY}
BASE_URL = "https://api.zotero.org"

GROUPS = {
    "p3579": os.environ["ZOTERO_GROUP_ID_P3579"],
    "p3998": os.environ["ZOTERO_GROUP_ID_P3998"],
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

def render_table(group_id, items):
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

def render_section(group_id, col_key, collections, children, depth=2):
    col     = collections[col_key]
    name    = col["name"]
    heading = "#" * depth
    output  = f"{heading} {name}\n\n"

    sub_keys = children.get(col_key, [])

    if sub_keys:
        for sub_key in sub_keys:
            output += render_section(
                group_id, sub_key, collections, children, depth + 1
            )
    else:
        items = get_items(group_id, col_key)
        output += render_table(group_id, items)

    return output

# ── Main ─────────────────────────────────────────────────────────────────────
for wg, group_id in GROUPS.items():
    label = "P3579" if wg == "p3579" else "P3998"
    output = f"# State of the Art — IEEE {label}\n\n"

    collections     = get_all_collections(group_id)
    roots, children = build_hierarchy(collections)

    for root_key in roots:
        output += render_section(group_id, root_key, collections, children)

    # Contributors section
    all_items    = get_all_items(group_id)
    contributors = get_contributors(all_items)
    if contributors:
        output += "\n---\n\n## Contributors\n\n"
        output += "*The following members have contributed references to this library:*\n\n"
        for c in contributors:
            output += f"- [{c}](https://www.zotero.org/{c})\n"
        output += "\n"

    with open(f"docs/{wg}/index.md", "w") as f:
        f.write(output)
    print(f"Generated docs/{wg}/index.md")
