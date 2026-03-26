import requests, os

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
    """Fetch all top-level items in the group library."""
    r = requests.get(
        f"{BASE_URL}/groups/{group_id}/items/top",
        params={"format": "json", "limit": 100},
        headers=HEADERS
    )
    return r.json()

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

def get_contributors(items):
    """Extract unique contributors from all items in the library."""
    contributors = set()
    for item in items:
        user = item.get("data", {}).get("createdByUser", {})
        if isinstance(user, dict):
            name = user.get("username", "")
            if name:
                contributors.add(name)
    return sorted(contributors)

def render_table(group_id, items):
    if not items:
        return "_No references yet._\n\n"

    # Sort by year, most recent first
    items = sorted(
        items,
        key=lambda i: str(i.get("data", {}).get("date", "0"))[:4],
        reverse=True,
    )

    output = "| Authors | Title | Year | DOI |\n"
    output += "|---------|-------|------|-----|\n"

    for item in items:
        d = item.get("data", {})
        authors = ", ".join(
            a.get("lastName", "") for a in d.get("creators", [])
        ) or "—"
        title   = d.get("title", "—")
        url     = d.get("url", "")
        year    = str(d.get("date", "—"))[:4]
        doi     = d.get("DOI", "—")

        # Clickable title if URL exists
        title_cell = f"[{title}]({url})" if url else title

        output += f"| {authors} | {title_cell} | {year} | {doi} |\n"

        # WG Notes
        notes = get_notes(group_id, item["data"]["key"])
        for note in notes:
            note_data = note.get("data", {})
            content   = clean_note(note_data.get("note", ""))
            creator   = note_data.get("createdByUser", {}).get("username", "WG")
            date      = note_data.get("dateAdded", "")[:10]
            if content:
                output += f"\n> 💬 **WG Note:** {content} *({creator}, {date})*\n\n"

    return output + "\n"

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

    # ── Contributors ─────────────────────────────────────────────────────────
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
