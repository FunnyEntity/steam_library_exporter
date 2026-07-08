# AGENTS.md — Steam Library Exporter

## Project overview

Extracts a Steam user's game library via 4 APIs (Steam Web, Store, Reviews, SteamSpy) and exports to CSV/JSON/SQLite with multilingual support. Python 3.11+ required — `tomllib` is stdlib, and CI only tests 3.11–3.13 (despite `pyproject.toml` saying `>=3.10`).

## Directory layout

```
steam_export.py              # CLI entry (interactive + argparse)
steam_export_gui.py          # GUI entry (with console, for debugging)
steam_export_gui.pyw         # GUI entry (no console — double-click on Windows)
sle/                         # core package
  engine.py                  # API calls, enrichment, export pipeline
  exporters.py               # CSVExporter / JSONExporter / SQLiteExporter
  gui.py                     # tkinter GUI
config/                      # all configuration
  .env                       # secrets (gitignored)
  settings.toml              # defaults (theme, language)
  col_groups.toml            # column group definitions (structural + multilingual labels)
  lang/                      # per-language translation files
    zh_cn.toml               # Chinese: gui, columns, genres, categories, game_names
    en_us.toml               # English: gui, columns (genres/categories optional)
frontend/                    # web UI (GitHub Pages)
  index.html                 # single-page app
  app.js                     # core logic
  style.css                  # responsive styling
  i18n/                      # JSON translations (built by CI from config/lang/)
scripts/
  build_i18n_json.py         # TOML → JSON converter for web frontend
  cors-proxy.js              # Cloudflare Worker for browser CORS proxy
```

## Entry points

| Command | What |
|---|---|
| `python steam_export.py` | Interactive mode (no args) or CLI mode (`--key ... --steamid ...`) |
| `python steam_export_gui.py` | GUI with console (for debugging) |
| Double-click `steam_export_gui.pyw` | GUI without console (Windows `pythonw.exe`) |
| `pip install .` → `steam-export` | Installs CLI entry point (see `pyproject.toml` `[project.scripts]`) |

## Commands

```
ruff check .              # lint (uses ruff defaults, no ruff.toml)
pip install -r requirements.txt   # install (only dependency: requests)
python steam_export.py --help     # see CLI flags
```

Key CLI flags: `--key`, `--steamid`, `--format`, `--sort`, `--sort-secondary`, `--min-playtime`, `--limit`, `--no-steamspy`, `--language`, `--columns`.

Use `--columns core` for 4 basic columns or `--columns "appid,name,genres"` for custom set.

There is no test suite. CI runs `ruff check .` + smoke test `python -c "import steam_export"` on Python 3.11/3.12/3.13.

## Secrets

- All secrets live in `config/.env` (gitignored).
- No other file contains secrets.
- `settings.toml` provides **non-secret defaults** (`theme`, `language`) used as fallbacks by `EnvManager`.

## How config loads

- **CLI**: `steam_export.py::_load_env_file()` reads `config/.env` and injects vars into `os.environ` on startup. No args → interactive mode, otherwise argparse with defaults from `os.environ`.
- **GUI**: `sle/gui.py::EnvManager` reads `config/.env` directly (not via os.environ), falling back to `config/settings.toml` defaults.
- **lang**: `sle/engine.py` auto-scans `config/lang/*.toml` at module import, builds `_LANG_DATA` dict used by `get_columns(lang)` / `get_genres(lang)` / etc. for runtime language selection. `sle/gui.py::Lang` loads per-language file at init and on lang switch.

## Translation system

Translations are split into per-language files under `config/lang/`. Column group structure is in `config/col_groups.toml`. Never hardcode translated strings in Python — always add a key to the lang files.

Each language file (`zh_cn.toml`, `en_us.toml`, ...) has sections: `[gui]` (UI text), `[columns]` (display names), `[genres]` / `[categories]` / `[game_names]` (data value translations).

Column groups (`col_groups.toml`) define `label_{lang}` / `desc_{lang}` per language alongside structural fields.

### Adding a new language

1. Create `config/lang/{lang}.toml` with `_label = "DisplayName"` in `[gui]`
2. Fill in translations for `[gui]` and `[columns]` (other sections optional)
3. Add `label_{lang}` / `desc_{lang}` to each group in `config/col_groups.toml`
4. Restart — language auto-appears in Settings dropdown and available as `--language` flag. Zero code changes.

Multi-word TOML keys MUST be quoted: `"Massively Multiplayer" = "中文"`.

## Key architecture notes

- **Export pipeline**: `run_export()` fetches → enriches each game (API calls) → sorts → delegates to `sle/exporters`.
- **Smart API skip**: `enrich_game()` checks `selected_columns` to skip Store/Reviews/SteamSpy API calls when none of their columns are requested. Core-only export is ~100× faster.
- **Rate limits**: `STORE_DELAY = 1.5s`, `STEAMSPY_DELAY = 1.0s` per game. Full export is slow (~30–40 min for ~500 games).
- **GUI thread safety**: Export runs in a `threading.Thread`. All UI updates via `root.after()`. Cancel uses `threading.Event`.
- **Hot language/theme switching**: Widgets have a `_lang_key` attribute. `_apply_language()` walks the widget tree and replaces text. Theme switches via `ttk.Style().theme_use()`.
- **Runtime language for export**: `enrich_game()` and `CSVExporter` accept a `lang` parameter. CLI uses `--language`, GUI passes `self.lang.lang`, GitHub Actions passes `language` workflow input. `run_export()` reads `cfg["lang"]`.
- **Web frontend**: vanilla JS SPA served via GitHub Pages. Uses a Cloudflare Worker (`scripts/cors-proxy.js`) to bypass CORS on Steam API. Worker URL is hardcoded in `frontend/app.js`; redeploy worker to change it. i18n JSON files are built by CI from `config/lang/*.toml` via `scripts/build_i18n_json.py`.
- **Version**: set in `pyproject.toml` only. `sle/engine.py::__version__` reads it automatically via `tomllib`.

## Known quirks

1. **`sys.stdout.reconfigure` in `sle/engine.py`** is wrapped in `try/except` because `pythonw.exe` (`.pyw` launch) has no stdout and would crash otherwise.
2. **Sort condition**: `engine.py:464` skips `sort_rows()` when sort is `"playtime"` with no secondary sort (rows stay in enrichment order which is pre-sorted by playtime). Remove the `if` guard to always sort.
3. **CSV encoding**: CSV files are written as `utf-8-sig` (BOM) for Excel compatibility on Windows.
4. **`.pyw` on Windows**: Only `.pyw` launches without console. The `.py` GUI entry still pops a console window.
