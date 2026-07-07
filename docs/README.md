# Steam Library Exporter

[![CI](https://github.com/funny_entity/steam_library_exporter/actions/workflows/ci.yml/badge.svg)](https://github.com/funny_entity/steam_library_exporter/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.1.0-blue)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()
[![Last Commit](https://img.shields.io/github/last-commit/funny_entity/steam_library_exporter)](https://github.com/funny_entity/steam_library_exporter/commits/main)
[![Open Issues](https://img.shields.io/github/issues/funny_entity/steam_library_exporter)](https://github.com/funny_entity/steam_library_exporter/issues)

Export your full Steam game library to CSV, JSON, or SQLite with rich metadata from four APIs.

---

## Why?

Steam shows you your library — it doesn't let you query it.
This tool pulls playtime, genres, prices, reviews, Metacritic scores, community tags, and estimated ownership data into a single flat CSV, JSON file, or SQLite database you can open in Excel, pandas, Google Sheets, Tableau, or any BI tool.

---

## Features

| Feature | Description |
|---|---|
| Interactive mode | Run without arguments for a guided step-by-step setup — no flags to memorize |
| 24 metadata columns | appid, name, playtime, genres, developers, publishers, release date, Metacritic score, prices, review counts, SteamSpy tags, and more |
| CSV, JSON & SQLite export | `--format csv` (default), `--format json`, or `--format sqlite` |
| GUI application | `steam_export_gui.py` / `.pyw` — point-and-click export with column selector |
| i18n support | Chinese and English UI with translatable game names, genres, and categories |
| Smart API skip | Only fetches data for columns you select — up to 100× faster for core-only export |
| Four API sources | Steam Web API, Steam Store API, Steam Reviews API, SteamSpy |
| Rich sort options | `--sort` supports 9 fields: playtime, playtime_2weeks, name, appid, metacritic, reviews, price, release_date, owners |
| Secondary sort | `--sort-secondary` for multi-key ordering |
| Filter unplayed | `--min-playtime N` to skip games under N hours |
| Environment variables | Set `STEAM_API_KEY` and `STEAM_ID` once — never retype credentials |
| Progress with ETA | Shows elapsed time and estimated time remaining per game |
| Export summary | Prints total playtime, played/unplayed counts, top genres, and avg Metacritic |
| Optional SteamSpy | Skip with `--no-steamspy` to cut export time by ~25% |
| Partial export | Use `--limit N` to test with a small batch before running the full library |
| Custom output path | Override the default filename with `--output` |
| Cross-platform | Runs on Windows, macOS, and Linux wherever Python 3.11+ is installed |
| GitHub Actions | Fork and run export directly on GitHub's servers — no local setup, no install needed |

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/davidmalko87/steam-library-exporter.git
cd steam-library-exporter
pip install -r requirements.txt
```

### 2. Configure

You need two things:

| Item | How to get it |
|---|---|
| Steam Web API key | [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey) (free) |
| Steam64 ID | [steamid.io](https://steamid.io) — 17-digit number |

> Set both **Profile** and **Game details** to **Public** in Steam → Settings → Privacy.

### 3. Run

```bash
# Interactive mode — guided step-by-step (no flags needed)
python steam_export.py

# Quick test — top 5 games by playtime
python steam_export.py --key YOUR_API_KEY --steamid YOUR_STEAM64_ID --limit 5

# Full library export
python steam_export.py --key YOUR_API_KEY --steamid YOUR_STEAM64_ID

# Use environment variables (set once, run without --key / --steamid)
export STEAM_API_KEY=YOUR_API_KEY
export STEAM_ID=YOUR_STEAM64_ID
python steam_export.py

# Export to JSON
python steam_export.py --key YOUR_API_KEY --steamid YOUR_STEAM64_ID --format json

# Export to SQLite database
python steam_export.py --key YOUR_API_KEY --steamid YOUR_STEAM64_ID --format sqlite

# Sort by name, with secondary sort by playtime
python steam_export.py --key YOUR_API_KEY --steamid YOUR_STEAM64_ID --sort name --sort-secondary playtime

# Sort by name, skip unplayed games
python steam_export.py --key YOUR_API_KEY --steamid YOUR_STEAM64_ID --sort name --min-playtime 1

# Faster — skip SteamSpy data
python steam_export.py --key YOUR_API_KEY --steamid YOUR_STEAM64_ID --no-steamspy

# Custom output filename
python steam_export.py --key YOUR_API_KEY --steamid YOUR_STEAM64_ID --output my_games.csv
```

---

## GitHub Actions

Run the export entirely on GitHub's servers — no Python, no terminal, no local setup needed.

### 1. Fork & set secrets

| Step | Action |
|---|---|
| Fork | Click the **Fork** button on the [GitHub repo](https://github.com/davidmalko87/steam-library-exporter) |
| Add secrets | Go to the forked repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** |
| `STEAM_API_KEY` | Paste your Steam Web API key (get one at [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)) |
| `STEAM_ID` | Paste your Steam64 ID (17-digit number, find at [steamid.io](https://steamid.io)) |

> Set both **Profile** and **Game details** to **Public** in Steam → Settings → Privacy.

### 2. Run the workflow

1. Go to your fork's **Actions** tab
2. Click **Export Steam Library** in the left sidebar
3. Click **Run workflow**
4. Choose your options and click the green **Run workflow** button

| Input | Default | Description |
|---|---|---|
| `format` | `csv` | Export format: `csv`, `json`, or `sqlite` |
| `limit` | `0` (all) | Number of games to export, ordered by playtime |
| `sort` | `playtime` | Sort field |
| `min_playtime` | `0` (all) | Minimum playtime in hours to include a game |
| `no_steamspy` | off | Skip SteamSpy API calls for faster export |

### 3. Download results

1. Once the workflow finishes, click on the run
2. Scroll down to **Artifacts**
3. Click **steam_library** to download the output file

> Artifacts are stored for 90 days on free GitHub accounts.

### 4. Scheduled runs (advanced)

The workflow is set to manual trigger only (`workflow_dispatch`). If you want automatic exports
(e.g., weekly), add an `on: schedule` trigger to your fork's copy of the workflow file.

---

## Configuration Reference

| Flag | Required | Default | Description |
|---|---|---|---|
| `--key KEY` | Yes* | — | Steam Web API key |
| `--steamid STEAMID` | Yes* | — | Steam64 ID (17-digit number) |
| `--output OUTPUT` | No | `steam_library.<format>` | Output file path |
| `--format FORMAT` | No | `csv` | Export format: `csv`, `json`, or `sqlite` |
| `--sort FIELD` | No | `playtime` | Sort by: `playtime`, `playtime_2weeks`, `name`, `appid`, `metacritic`, `reviews`, `price`, `release_date`, or `owners` |
| `--sort-secondary FIELD` | No | — | Secondary sort key (same options as `--sort`) |
| `--min-playtime N` | No | `0` (all) | Minimum playtime in hours to include a game |
| `--no-steamspy` | No | off | Skip SteamSpy API calls (faster export) |
| `--limit N` | No | `0` (all) | Export only the top N games by playtime |
| `--version` | No | — | Print version and exit |

*\* Not required if the corresponding environment variable is set.*

### Environment Variables

| Variable | Replaces | Description |
|---|---|---|
| `STEAM_API_KEY` | `--key` | Steam Web API key |
| `STEAM_ID` | `--steamid` | Steam64 ID |
| `THEME` | — | ttk theme name (e.g., `clam`, `vista`); used by GUI |
| `LANGUAGE` | — | UI language: `zh` (Chinese) or `en` (English) |
| `SELECTED_COLUMNS` | — | Comma-separated list of columns to export; used by GUI |

---

## Output Columns

`appid`, `name`, `playtime_hours`, `playtime_2weeks_hours`, `type`, `developers`, `publishers`, `genres`, `categories`, `release_date`, `metacritic_score`, `price_current`, `price_initial`, `is_free`, `short_description`, `header_image`, `total_positive`, `total_negative`, `review_score_desc`, `total_reviews`, `estimated_owners`, `avg_playtime_global`, `median_playtime_global`, `steamspy_tags`

### Sample rows

```
appid,name,playtime_hours,metacritic_score,genres,price_current,review_score_desc,estimated_owners
570,Dota 2,1842.3,90,Action;Free to Play,0.0,Overwhelmingly Positive,100000000-200000000
730,Counter-Strike 2,634.1,83,Action,0.0,Very Positive,50000000-100000000
1091500,Cyberpunk 2077,112.7,86,Action;RPG,29.99,Very Positive,10000000-20000000
```

---

## Project Structure

```
steam-library-exporter/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml
│   │   └── feature_request.yml
│   ├── workflows/
│   │   ├── ci.yml           # Lint & smoke test
│   │   ├── export.yml       # Run export on GitHub Actions
│   │   └── publish.yml      # PyPI release
│   └── PULL_REQUEST_TEMPLATE.md
├── config/
│   ├── .env               # Secrets (API key, Steam ID, theme, language)
│   ├── .env.example        # Template for new users
│   ├── i18n.toml           # Chinese/English translations
│   └── settings.toml       # Default theme and language
├── docs/
│   ├── README.md
│   ├── CHANGELOG.md
│   └── CONTRIBUTING.md
├── sle/
│   ├── engine.py           # API calls, enrichment, export pipeline
│   ├── exporters.py        # CSV / JSON / SQLite exporters
│   └── gui.py              # tkinter GUI
├── steam_export.py         # CLI entry point
├── steam_export_gui.py     # GUI entry (with console)
├── steam_export_gui.pyw    # GUI entry (no console, double-click on Windows)
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

---

## Known Limitations

- **Rate limits**: Steam Store API requires ~1.5 s between requests. A 200-game library takes roughly 13 minutes.
- **Private profiles**: The tool cannot read libraries set to Private in Steam Privacy Settings.
- **Free-to-play games**: Some F2P titles may lack price data in the Store API response.
- **SteamSpy accuracy**: Estimated ownership ranges are approximate (SteamSpy infers data, Steam does not publish it).
- **No incremental export**: The script always fetches and writes the full library from scratch.
- **GitHub Actions**: Free-tier accounts have 2000 minutes/month; export of 200 games takes ~30–40 min. Workflows time out after 6 hours (generous).

---

## Security

> Never commit your API key. The `.gitignore` excludes common credential files (`.env`, `*.key`), but always verify before pushing.

Your Steam Web API key is read-only and scoped to public data, but treat it like any credential.

---

## License

[MIT](LICENSE) © 2026 David Malko

---

## Links

- [Changelog](CHANGELOG.md)
- [Contributing guide](CONTRIBUTING.md)
- [Open an issue](https://github.com/davidmalko87/steam-library-exporter/issues)
