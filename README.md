# State of the Art on AI and Time Series

**IEEE AI & Time Series Working Group**

Public documentation site for the **IEEE AI & Time Series Working Group**, automatically synchronized with Zotero group libraries.

🌐 **Live site:** [aitimeseries.github.io/SOTA](https://aitimeseries.github.io/SOTA/)

---

## Overview

This repository powers a curated, continuously updated bibliography of state-of-the-art references for the IEEE AI & Time Series Working Group, which develops two standards projects:

- **[IEEE P3579](https://aitimeseries.github.io/SOTA/p3579/)** — AI Systems Applied to Time Series
- **[IEEE P3998](https://aitimeseries.github.io/SOTA/p3998/)** — Time Series Applied to AI Systems

References are managed in [Zotero](https://www.zotero.org/) group libraries and automatically published to a static site built with [MkDocs Material](https://squidfund.github.io/mkdocs-material/).

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
  GitHub Pages           → aitimeseries.github.io/SOTA
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
│   └── p3998/index.md       # IEEE P3998 references (auto-generated)
├── scripts/
│   └── generate_sota.py     # Zotero API sync script
├── mkdocs.yml               # MkDocs configuration
└── README.md
```

## Zotero Integration

References are organized in Zotero group libraries (one per standards project) using **collections** that map to sections on the site (Standards, Resources, Publications, etc.). The sync script:

1. Fetches all collections and items from each Zotero group via the API
2. Builds a hierarchy of sections from the collection structure
3. Renders Markdown tables with authors, title, year, DOI, and links
4. Includes working group notes attached to references
5. Sorts references by year (most recent first)

### Adding References

To add a new reference, simply add it to the appropriate Zotero group library and collection. The next sync will pick it up automatically, or you can trigger the workflow manually from the Actions tab.

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
python scripts/generate_sota.py
```

## Workflows

### Deploy (`deploy.yml`)

- **Trigger:** Push to `main` or manual dispatch
- **Action:** Builds the MkDocs site and deploys to the `gh-pages` branch
- **Site:** Served via GitHub Pages at `aitimeseries.github.io/SOTA`

### Zotero Sync (`sync-zotero.yml`)

- **Trigger:** Weekly (Monday 08:00 UTC) or manual dispatch
- **Action:** Runs `generate_sota.py`, commits changes, and opens a Pull Request for review
- **Branch:** Changes are pushed to `zotero-sync` branch

## License

This project is maintained by the [IEEE AI & Time Series Working Group](https://github.com/aitimeseries).
