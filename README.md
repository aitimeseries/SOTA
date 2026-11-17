# State of the Art on AI and Time Series

Public documentation site for the **IEEE AI & Time Series Working Group**, automatically synchronized with Zotero group libraries.

🌐 **Live site:** [aitimeseries.com](https://aitimeseries.com)

---

## Overview

This repository powers a curated, continuously updated bibliography of state-of-the-art references for the IEEE AI & Time Series Working Group, which develops two standards projects:

- **[IEEE P3579](https://aitimeseries.com/p3579/)** — AI Systems Applied to Time Series
- **[IEEE P3998](https://aitimeseries.com/p3998/)** — Time Series Applied to AI Systems

References common to both projects are published on a joint page: **[Joint P3579 & P3998](https://aitimeseries.com/p3579-p3998/)**.

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
│   └── sync-zotero.yml      # Fetch references from Zotero → open PR
├── docs/
│   ├── index.md             # Home page
│   ├── p3579/index.md       # IEEE P3579 references (auto-generated)
│   ├── p3998/index.md       # IEEE P3998 references (auto-generated)
│   └── p3579-p3998/index.md # References common to P3579 & P3998 (auto-generated)
├── scripts/
│   └── generate_sota.py     # Zotero API sync script
├── mkdocs.yml               # MkDocs configuration
└── README.md
```

## Zotero Integration

References are organized in Zotero group libraries (one per standards project, plus a joint library for the references common to both) using **collections** that map to sections on the site (Standards, Resources, Publications, etc.). The sync script:

1. Fetches all collections and items from each Zotero group via the API
2. Builds a hierarchy of sections from the collection structure
3. Renders Markdown tables with authors, title, year, DOI, and links
4. Includes working group notes attached to references
5. Sorts references by year (most recent first)

### Adding References

To add a new reference, simply add it to the appropriate Zotero group library and collection. The next sync will pick it up automatically, or you can trigger the workflow manually from the Actions tab.

A reference relevant to both projects belongs in the joint library only: move it there rather than copying it, otherwise it shows up on several pages.

## Setup

### Prerequisites

- A GitHub account with access to this repository
- Zotero group libraries for P3579, P3998, and the references common to both (joint library)
- A [Zotero API key](https://www.zotero.org/settings/keys) with read access to the groups

### Repository Secrets

The following secrets must be configured in the repository settings (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `ZOTERO_API_KEY` | Zotero API key with read access |
| `ZOTERO_GROUP_ID_P3579` | Zotero group ID for IEEE P3579 |
| `ZOTERO_GROUP_ID_P3998` | Zotero group ID for IEEE P3998 |
| `ZOTERO_GROUP_ID_P3579_P3998` | Zotero group ID for the joint P3579 & P3998 library |

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
export ZOTERO_GROUP_ID_P3579_P3998=your_group_id
python scripts/generate_sota.py
```

## Workflows

### Deploy (`deploy.yml`)

- **Trigger:** Push to `main` or manual dispatch
- **Action:** Builds the MkDocs site and deploys to the `gh-pages` branch
- **Site:** Served via GitHub Pages at `aitimeseries.com`

### Zotero Sync (`sync-zotero.yml`)

- **Trigger:** Weekly (Monday 08:00 UTC) or manual dispatch
- **Action:** Runs `generate_sota.py`, commits changes, and opens a Pull Request for review
- **Branch:** Changes are pushed to `zotero-sync` branch

### Move Zotero References (`zotero-move.yml`)

Moves references from one group library to another (for example, a reference that turns out to be common to both projects, from P3579 to the joint library). Zotero has no move between libraries, so for each reference `scripts/zotero_move.py`:

1. copies it, with its notes, into the target group's collections;
2. verifies the copy: every field equal to the source's (except key, version, collections, relations and dates), the target collections, the same notes, and no other child;
3. sends the source item to the source group's **trash**, where it can be restored. The tool never deletes.

How to run a batch:

1. List the moves in `scripts/zotero_moves.json` and leave `"apply": false`. Each entry gives `source` and `target` (`p3579`, `p3998` or `p3579-p3998`), the item `key`, its exact `title`, and `to`, the target collection paths, such as `RESOURCES/Models`. An item with attachments (e.g. a web-page snapshot) is refused unless its entry says `"attachments": "leave"`: the copy is then made without them, and they stay only with the source item in its group's trash, so they are lost when that trash is emptied.
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
