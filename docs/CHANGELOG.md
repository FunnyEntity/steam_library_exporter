# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] — 2026-07-07

### Added
- **SQLite export**: `--format sqlite` writes a local database alongside CSV and JSON.
- **GUI application**: `steam_export_gui.py` / `.pyw` with column selector, language/theme switching.
- **i18n support**: Chinese and English UI with translatable game names, genres, and categories.
- **Smart API skip**: only fetches data for selected columns — up to 100× faster for core-only export.
- **Secondary sort**: `--sort-secondary` for multi-key ordering.
- **GitHub Actions**: run export directly on GitHub's servers via `workflow_dispatch`.
- Additional sort fields: `playtime_2weeks`, `appid`, `price`, `release_date`, `owners`.
- SteamSpy tags column in output.

### Changed
- Require Python 3.10+ (previously 3.11+).
- Export pipeline decoupled from CLI for reuse by GUI.

---

## [1.1.0] — 2026-04-13

### Added
- **Interactive mode**: run without arguments for a guided step-by-step setup (credentials, format, sort, filters — all prompted with defaults).
- **Environment variable support**: set `STEAM_API_KEY` and `STEAM_ID` to skip typing credentials every run; works in both CLI and interactive modes.
- **JSON export**: `--format json` writes a structured JSON array alongside the existing CSV support.
- **Sort options**: `--sort playtime|name|metacritic|reviews` to control output order (default: playtime descending).
- **Min-playtime filter**: `--min-playtime N` skips games with fewer than N hours played.
- **Progress with ETA**: each game now shows elapsed time and estimated time remaining during export.
- **Export summary**: after writing, prints total playtime, played/unplayed counts, average Metacritic score, and top genres.
- **`--version` flag**: prints the current version and exits.

### Changed
- `--key` and `--steamid` are no longer required when their corresponding environment variables are set.
- Default output filename adapts to format: `steam_library.csv` or `steam_library.json`.

---

## [1.0.0] — 2026-03-26

### Added
- `steam_export.py`: CLI tool to export a Steam library to CSV with 24 columns of metadata.
- Pulls data from four APIs: Steam Web API, Steam Store API, Steam Reviews API, and SteamSpy.
- `--key`, `--steamid`, `--output`, `--limit`, and `--no-steamspy` CLI flags.
- Rate-limiting delays (1.5 s / Store, 1.0 s / SteamSpy) to respect upstream limits.
- `requirements.txt` pinning `requests>=2.28.0`.
- `.gitignore` covering common Python artefacts and sensitive credential files.
- `LICENSE` (MIT, © 2026 David Malko).
- `README.md` with badges, usage examples, output column reference, and performance notes.
- `__version__` constant (`1.0.0`) in `steam_export.py`.

---

<!-- insertion point — add new entries above this line -->
