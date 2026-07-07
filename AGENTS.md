# AGENTS.md — Steam Library Exporter

## Project overview

Extracts a Steam user's game library via 4 APIs (Steam Web, Store, Reviews, SteamSpy) and exports to CSV/JSON/SQLite with i18n support. Python 3.11+ required (uses `tomllib` from stdlib).

## Directory layout

```
steam_export.py              # CLI entry (interactive + argparse)
steam_export_gui.py          # GUI entry (with console)
steam_export_gui.pyw         # GUI entry (no console, double-click on Windows)
sle/                         # core package
  engine.py                  # API calls, enrichment, export pipeline
  exporters.py               # CSVExporter / JSONExporter / SQLiteExporter
  gui.py                     # tkinter GUI: main window, settings/column dialogs
config/                      # all configuration
  .env                       # secrets (gitignored) — API key, Steam64 ID, theme, language
  .env.example               # template for new users
  i18n.toml                  # translations: columns, genres, categories, game names, GUI text
  settings.toml              # default settings (theme, language)
docs/                        # README, CHANGELOG, CONTRIBUTING
```

## Secrets

- All secrets live in `config/.env` (gitignored).
- New users copy `config/.env.example` → `config/.env` and fill in real values.
- No other file contains secrets. Running `git push` requires zero manual cleanup.

## Entry points

| Command | What |
|---|---|
| `python steam_export.py` | Interactive mode (no args) or CLI mode (`--key ... --steamid ...`) |
| `python steam_export_gui.py` | GUI with console (for debugging) |
| Double-click `steam_export_gui.pyw` | GUI without console (Windows `pythonw.exe`) |

## How config loads

- **CLI**: `steam_export.py::_load_env_file()` reads `config/.env` and injects vars into `os.environ` on startup. No args → interactive mode, otherwise argparse with defaults from `os.environ`.
- **GUI**: `sle/gui.py::EnvManager` reads `config/.env` directly (not via os.environ).
- **i18n**: `sle/engine.py` loads `config/i18n.toml` at module import time via `tomllib`. Same for `sle/gui.py::I18n`.

## Translation system (i18n.toml)

All translations are in `config/i18n.toml`. Adding a translation = adding one line to the right TOML section. Never hardcode translated strings in Python.

Sections:
- `[columns]` — CSV header Chinese names
- `[genres]` / `[categories]` — data value translations
- `[game_names]` — optional game name translations (empty by default)
- `[col_groups.*]` — column group definitions for the GUI column selector
- `[gui.zh]` / `[gui.en]` — every GUI label indexed by key name

Multi-word TOML keys MUST be quoted: `"Massively Multiplayer" = "中文"`.

## Key architecture notes

- **Export pipeline**: `run_export()` fetches games → enriches each game (API calls) → sorts → delegates to `sle/exporters`.
- **Exporters**: `sle/exporters.py` factory `get_exporter(fmt)` returns CSV/JSON/SQLite instances. Internal sort fields (`_sort_*`) are filtered out by `_resolve_columns()`. SQLite uses `DROP TABLE IF EXISTS` + `CREATE TABLE` (overwrite mode).
- **Smart API skip**: `enrich_game()` checks `selected_columns` to skip Store/Reviews/SteamSpy API calls when none of their columns are requested. If only core columns (appid, name, playtime) are selected, export is ~100× faster.
- **Rate limits**: `STORE_DELAY = 1.5s`, `STEAMSPY_DELAY = 1.0s` per game. ~543 games ≈ 30-40 min full export.
- **GUI thread safety**: Export runs in a `threading.Thread`. All UI updates dispatched via `root.after()`. Cancel uses `threading.Event`.
- **Hot language/theme switching**: Every widget has a `_i18n_key` attribute. `_apply_language()` walks the widget tree and replaces text. Theme switches via `ttk.Style().theme_use()`.

## Dependencies

- **Only `requests`** in `requirements.txt`. `tomllib` is Python 3.11+ stdlib. `tkinter` is stdlib. `sqlite3` is stdlib. No other dependencies needed.
- No build step. Run `pip install -r requirements.txt` once.

## Known quirks

1. **`sys.stdout.reconfigure` in `sle/engine.py`** is wrapped in `try/except` because `pythonw.exe` (`.pyw` launch) has no stdout and would crash otherwise.
2. **Sort condition**: `engine.py:465` has `if sort_key != "playtime" or sort_secondary:` before `sort_rows()`. When sort is "playtime" with no secondary, sorting is skipped (rows keep the enrichment order which is pre-sorted by playtime). If changing this behavior, remove the `if` guard and always call `sort_rows()`.
3. **CSV encoding**: CSV files are written as `utf-8-sig` (BOM) for Excel compatibility on Windows.
4. **`.pyw` on Windows**: Only `.pyw` launches without console. The `.py` GUI entry still pops a console window.
