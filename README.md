# State of the Art on AI and Time Series

Public documentation site for the **IEEE AI & Time Series Working Group**, automatically synchronized with Zotero group libraries.

🌐 **Live site:** [aitimeseries.com](https://aitimeseries.com)

---

## Overview

This repository powers a curated, continuously updated bibliography of state-of-the-art references for the IEEE AI & Time Series Working Group, which develops two standards projects:

- **[IEEE P3579](https://aitimeseries.com/p3579/)** — AI Systems Applied to Time Series
- **[IEEE P3998](https://aitimeseries.com/p3998/)** — Time Series Applied to AI Systems

References present in both project libraries are also shown on a joint page, computed by the sync: **[Joint P3579 & P3998](https://aitimeseries.com/p3579-p3998/)**. How a reference is classified under P3579, P3998 or both is explained on the site: **[How references are classified](https://aitimeseries.com/classification/)**.

References are managed in [Zotero](https://www.zotero.org/) group libraries and automatically published to a static site built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

## How It Works

```
Zotero Group Libraries
        │
        ▼
  sync-zotero.yml       ← Runs weekly (Monday 08:00 UTC) or on demand
  (generate_sota.py)       Fetches references via Zotero API
        │                  Generates Markdown tables in docs/
        ▼
  Pull Request           ← Opened automatically for review
        │
        ▼  (merge)
  deploy.yml             ← Triggered on push to main
  (mkdocs build)           Builds HTML with MkDocs Material
        │                  Deploys to gh-pages branch
        ▼
  GitHub Pages           → aitimeseries.com
```

## Repository Structure

```
SOTA/
├── .github/workflows/
│   ├── deploy.yml           # Build & deploy site to GitHub Pages
│   ├── sync-zotero.yml      # Fetch references from Zotero → open PR
│   └── zotero-move.yml      # Move references between groups (dry run, then apply)
├── docs/
│   ├── index.md             # Home page (its "latest updates" blocks, between the <!-- latest:… --> markers, are rewritten by the sync: do not edit them by hand)
│   ├── p3579/index.md       # IEEE P3579 references (auto-generated)
│   ├── p3998/index.md       # IEEE P3998 references (auto-generated)
│   ├── p3579-p3998/index.md # References in both P3579 and P3998 (auto-generated, computed)
│   ├── classification.md    # How references are classified (criteria for contributors)
│   └── stylesheets/terminal.css # Terminal style of the home page's "latest updates" blocks
├── scripts/
│   ├── generate_sota.py     # Zotero API sync script
│   ├── joint.py             # Joint-page rules (matching, sections, notes), no network
│   ├── check_matching.py    # Offline checks of joint.py, run before each sync
│   ├── zotero_move.py       # Move script (copy, verify, trash)
│   └── zotero_moves.json    # Moves manifest (reviewed like code)
├── mkdocs.yml               # MkDocs configuration
└── README.md
```

## Zotero Integration

References are organized in Zotero group libraries, one per standards project (IEEE-P3579 and IEEE-P3998), using **collections** that map to sections on the site (Publications, Resources, Standards). The joint page is not a library: the sync computes it from the references present in both groups. The sync script:

1. Fetches all collections and items from each Zotero group via the API
2. Builds a hierarchy of sections from the collection structure
3. Renders Markdown tables with authors, title, year, DOI, and links
4. Includes working group notes attached to references
5. Sorts references by year (most recent first)

### Adding References

To add a new reference, add it to the Zotero group of the project it belongs to, following the criteria on [How references are classified](docs/classification.md). The next sync will pick it up automatically, or you can trigger the workflow manually from the Actions tab.

- **Both projects:** add it to one group, then drag it onto the same section of the other group in Zotero desktop. The drag copies the reference with its notes and links the copy to the original, which the sync uses to recognize them as one reference; it then appears on the P3579, P3998 and joint pages. Without that link, the sync falls back to the same DOI, then the same URL.
- **File it in a section that has no sub-sections:** a reference filed on a section with sub-sections, or on no section, is on no page (the sync names it in a warning).

## Setup

### Prerequisites

- A GitHub account with access to this repository
- Zotero group libraries for P3579 and P3998
- A [Zotero API key](https://www.zotero.org/settings/keys) with read access to the groups

### Repository Secrets

The following secrets must be configured in the repository settings (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `ZOTERO_API_KEY` | Zotero API key with read access |
| `ZOTERO_GROUP_ID_P3579` | Zotero group ID for IEEE P3579 |
| `ZOTERO_GROUP_ID_P3998` | Zotero group ID for IEEE P3998 |

### Local Development

```bash
# Clone the repository
git clone https://github.com/aitimeseries/SOTA.git
cd SOTA

# Install dependencies
pip install mkdocs-material requests

# Preview the site locally
mkdocs serve

# Run Zotero sync manually (requires environment variables)
export ZOTERO_API_KEY=your_key
export ZOTERO_GROUP_ID_P3579=your_group_id
export ZOTERO_GROUP_ID_P3998=your_group_id
python scripts/check_matching.py   # offline checks of the joint-page rules
python scripts/generate_sota.py
```

## Workflows

### Deploy (`deploy.yml`)

- **Trigger:** Push to `main` or manual dispatch
- **Action:** Builds the MkDocs site and deploys to the `gh-pages` branch
- **Site:** Served via GitHub Pages at `aitimeseries.com`

### Zotero Sync (`sync-zotero.yml`)

- **Trigger:** Weekly (Monday 08:00 UTC) or manual dispatch
- **Action:** Checks the joint-page rules offline (`check_matching.py`), runs `generate_sota.py`, builds the site with `mkdocs build --strict` (no deploy) and keeps it 7 days as the run's `site-preview` artifact, commits changes, and opens a Pull Request for review
- **Branch:** Changes are pushed to `zotero-sync` branch

### Move Zotero References (`zotero-move.yml`)

Moves references from one project group to the other (for example, a reference filed in the wrong project). To make a reference common to both projects, do not move it: copy it into the other group (see [Adding References](#adding-references)). Zotero has no move between libraries, so for each reference `scripts/zotero_move.py`:

1. copies it, with its notes, into the target group's collections;
2. verifies the copy: every field equal to the source's (except key, version, collections, relations and dates), the target collections, the same notes, and no other child;
3. sends the source item to the source group's **trash**, where it can be restored. The tool never deletes.

How to run a batch:

1. List the moves in `scripts/zotero_moves.json` and leave `"apply": false`. Each entry gives `source` and `target` (`p3579` or `p3998`), the item `key`, its exact `title`, and `to`, the target collection paths, such as `RESOURCES/Models`. An item with attachments (e.g. a web-page snapshot) is refused unless its entry says `"attachments": "leave"`: the copy is then made without them, and they stay only with the source item in its group's trash, so they are lost when that trash is emptied.
2. Dispatch the workflow without `apply`: the `plan` job reads only and prints what would be written. A dispatch with `--ref <branch>` runs that branch's manifest and script, for the dry run only.
3. Set `"apply": true` and bring it to `main` through a reviewed pull request, then dispatch on `main` with `apply` checked. The `apply` job runs in the `zotero-write` Environment, which accepts jobs from `main` only, and waits for its required reviewer's approval: read the same run's `plan` log first, and reject if it differs from the reviewed dry run. (To apply from another branch, the Environment needs a temporary branch policy for it, removed afterwards.)
4. Reset the manifest to `"apply": false` with an empty `moves` list. Git keeps the history of what was moved.

Guards: the run stops if a title differs from the manifest, if an item has attachments and its entry does not say `"attachments": "leave"`, if a target collection is not a leaf (references filed on a collection with sub-collections are not published), or if a copy does not match its source. A reference already moved (source in the trash and a verified copy in the target) is skipped.

Keys: the `plan` job reads with `ZOTERO_API_KEY`, which needs read access only. The `apply` job writes with `ZOTERO_WRITE_API_KEY`, a secret of the `zotero-write` Environment, which needs write access to the site's groups only.

## Custom Domain

The site is served at `aitimeseries.com` via GitHub Pages. The domain also hosts subdomains for the IEEE standards project pages.

### DNS Records

| Type | Host | Value |
|------|------|-------|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `aitimeseries.github.io` |
| CNAME | `p3579` | *(IEEE SA — existing)* |
| CNAME | `p3998` | *(IEEE SA — pending)* |

### GitHub Pages Configuration

In the repo Settings → Pages:
- **Source:** Deploy from a branch
- **Branch:** `gh-pages` / `/ (root)`
- **Custom domain:** `aitimeseries.com`
- **Enforce HTTPS:** enabled

### CNAME Persistence

The `deploy.yml` workflow includes `cname: aitimeseries.com` in the `peaceiris/actions-gh-pages` step to ensure the `CNAME` file is preserved on every deployment. Without this, each deploy would overwrite the `gh-pages` branch and remove the custom domain configuration.

*This project is maintained by the [IEEE AI & Time Series Working Group](https://github.com/aitimeseries).*
