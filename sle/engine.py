"""
sle.engine — Steam Library Exporter core engine
================================================
Handles API calls, data enrichment, export pipeline, and i18n loading.
"""

import re
import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path

import requests

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

__version__ = "1.2.0"

# --- Load i18n config ---
_I18N_PATH = Path(__file__).parent.parent / "config" / "i18n.toml"
with open(_I18N_PATH, "rb") as _f:
    _i18n = tomllib.load(_f)

CN_COLUMNS = _i18n.get("columns", {})
GENRE_CN = _i18n.get("genres", {})
CATEGORY_CN = _i18n.get("categories", {})
GAME_NAME_CN = _i18n.get("game_names", {})
COL_GROUPS = _i18n.get("col_groups", {})

# --- Endpoints ---
OWNED_GAMES_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
APP_REVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"
STEAMSPY_URL = "https://steamspy.com/api.php"

# --- Rate limit delays (seconds) ---
STORE_DELAY = 1.5
STEAMSPY_DELAY = 1.0

# --- Sort keys: key → (field, ascending) ---
SORT_OPTIONS: dict[str, tuple[str, bool]] = {
    "playtime":        ("playtime_hours",         False),
    "playtime_2weeks": ("playtime_2weeks_hours",  False),
    "name":            ("name",                   True),
    "appid":           ("appid",                  True),
    "metacritic":      ("metacritic_score",       False),
    "reviews":         ("total_reviews",          False),
    "price":           ("_sort_price",             False),
    "release_date":    ("_sort_date",              False),
    "owners":          ("_sort_owners",            False),
}

# --- All known columns ---
ALL_COLUMNS = list(CN_COLUMNS.keys())

# --- Column -> group mapping ---
COLUMN_GROUPS: dict[str, str] = {}
GROUP_FIELDS: dict[str, list[str]] = {}
for group_key, group_data in COL_GROUPS.items():
    fields = group_data.get("fields", [])
    GROUP_FIELDS[group_key] = fields
    for f in fields:
        COLUMN_GROUPS[f] = group_key

CORE_COLUMNS = {"appid", "name", "playtime_hours", "playtime_2weeks_hours"}
STORE_COLUMNS = set(GROUP_FIELDS.get("store", []))
REVIEWS_COLUMNS = set(GROUP_FIELDS.get("reviews", []))
STEAMSPY_COLUMNS = set(GROUP_FIELDS.get("steamspy", []))


# ── Sort value parsers ────────────────────────────────────────────────

def _parse_price(val) -> float:
    if not val or val == "":
        return -1.0
    m = re.search(r'[\d,]+\.?\d*', str(val))
    return float(m.group().replace(",", "")) if m else -1.0


def _parse_date(val) -> int:
    if not val or val == "":
        return 0
    for fmt in ("%b %d, %Y", "%d %b, %Y", "%d %B, %Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(val, fmt)
            return dt.year * 10000 + dt.month * 100 + dt.day
        except ValueError:
            continue
    return 0


def _parse_owners(val) -> int:
    if not val or val == "":
        return 0
    m = re.match(r'[\d,]+', str(val))
    return int(m.group().replace(",", "")) if m else 0


def _add_sort_fields(row: dict):
    row["_sort_price"] = _parse_price(row.get("price_current", ""))
    row["_sort_date"] = _parse_date(row.get("release_date", ""))
    row["_sort_owners"] = _parse_owners(row.get("estimated_owners", ""))


# ── Translation helper ────────────────────────────────────────────────

def translate_list(text: str, mapping: dict) -> str:
    if not text:
        return ""
    items = [s.strip() for s in text.split(", ") if s.strip()]
    return ", ".join(mapping.get(item, item) for item in items)


# ── API functions ─────────────────────────────────────────────────────

def get_owned_games(api_key: str, steam_id: str,
                     log_func=None) -> list[dict]:
    def log(msg): log_func(msg) if log_func else print(msg)

    params = {
        "key": api_key,
        "steamid": steam_id,
        "include_appinfo": 1,
        "include_played_free_games": 1,
        "format": "json",
    }
    resp = requests.get(OWNED_GAMES_URL, params=params, timeout=30)

    if resp.status_code != 200:
        msg = (f"GetOwnedGames returned HTTP {resp.status_code}\n"
               f"Response: {resp.text[:500]}")
        log(f"[ERROR] {msg}")
        raise RuntimeError(msg)

    data = resp.json().get("response", {})
    games = data.get("games", [])

    if not games:
        msg = ("Got empty games list.\n"
               "Possible causes:\n"
               "  - Profile or game details set to PRIVATE\n"
               "  - Incorrect Steam64 ID (must be 17-digit number)\n"
               "  - API key revoked or invalid")
        log(f"[ERROR] {msg}")
        raise RuntimeError(msg)

    log(f"[OK] Found {len(games)} games in library.")
    return games


def get_store_details(appid: int, log_func=None) -> dict:
    def log(msg): log_func(msg) if log_func else print(msg)
    try:
        resp = requests.get(
            APP_DETAILS_URL,
            params={"appids": appid, "l": "english", "cc": "cn"},
            timeout=15,
        )
        if resp.status_code != 200:
            return {}
        result = resp.json()
        app_data = result.get(str(appid), {})
        if not app_data.get("success"):
            return {}
        return app_data.get("data", {})
    except Exception as e:
        log(f"  [WARN] Store API failed for {appid}: {e}")
        return {}


def get_review_summary(appid: int) -> dict:
    try:
        resp = requests.get(
            APP_REVIEWS_URL.format(appid=appid),
            params={
                "json": 1,
                "language": "all",
                "purchase_type": "all",
                "num_per_page": 0,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return {}
        data = resp.json().get("query_summary", {})
        return {
            "total_positive": data.get("total_positive", ""),
            "total_negative": data.get("total_negative", ""),
            "review_score_desc": data.get("review_score_desc", ""),
            "total_reviews": data.get("total_reviews", ""),
        }
    except Exception:
        return {}


def get_steamspy_data(appid: int) -> dict:
    try:
        resp = requests.get(
            STEAMSPY_URL,
            params={"request": "appdetails", "appid": appid},
            timeout=15,
        )
        if resp.status_code != 200:
            return {}
        data = resp.json()
        tags = data.get("tags", {})
        tag_str = ", ".join(tags.keys()) if isinstance(tags, dict) else ""
        return {
            "estimated_owners": data.get("owners", ""),
            "avg_playtime_global": data.get("average_forever", ""),
            "median_playtime_global": data.get("median_forever", ""),
            "steamspy_tags": tag_str,
        }
    except Exception:
        return {}


# ── Enrichment ────────────────────────────────────────────────────────

def enrich_game(game: dict, use_steamspy: bool = True,
                selected_columns: set | None = None,
                log_func=None) -> dict:
    def log(msg): log_func(msg) if log_func else print(msg)

    appid = game["appid"]
    name = game.get("name", f"Unknown ({appid})")
    playtime_hrs = round(game.get("playtime_forever", 0) / 60, 1)
    playtime_2wk = round(game.get("playtime_2weeks", 0) / 60, 1)

    name = GAME_NAME_CN.get(name, name)

    row = {
        "appid": appid,
        "name": name,
        "playtime_hours": playtime_hrs,
        "playtime_2weeks_hours": playtime_2wk,
    }

    if selected_columns is None:
        need_store = True
        need_reviews = True
        need_spy = use_steamspy
    else:
        need_store = bool(STORE_COLUMNS & selected_columns)
        need_reviews = bool(REVIEWS_COLUMNS & selected_columns)
        need_spy = use_steamspy and bool(STEAMSPY_COLUMNS & selected_columns)

    if need_store:
        store = get_store_details(appid, log_func=log_func)
        if store:
            genres = store.get("genres", [])
            categories = store.get("categories", [])
            price_data = store.get("price_overview", {})

            row["type"] = store.get("type", "")
            row["developers"] = ", ".join(store.get("developers", []))
            row["publishers"] = ", ".join(store.get("publishers", []))
            row["genres"] = translate_list(
                ", ".join(g["description"] for g in genres), GENRE_CN,
            )
            row["categories"] = translate_list(
                ", ".join(c["description"] for c in categories), CATEGORY_CN,
            )
            row["release_date"] = store.get("release_date", {}).get("date", "")
            row["metacritic_score"] = store.get("metacritic", {}).get("score", "")
            row["price_current"] = price_data.get("final_formatted", "")
            row["price_initial"] = price_data.get("initial_formatted", "")
            row["is_free"] = store.get("is_free", "")
            row["short_description"] = store.get("short_description", "")
            row["header_image"] = store.get("header_image", "")
        else:
            for k in STORE_COLUMNS:
                row[k] = ""
        time.sleep(STORE_DELAY)
    else:
        for k in STORE_COLUMNS:
            row[k] = ""

    if need_reviews:
        reviews = get_review_summary(appid)
        row["total_positive"] = reviews.get("total_positive", "")
        row["total_negative"] = reviews.get("total_negative", "")
        row["review_score_desc"] = reviews.get("review_score_desc", "")
        row["total_reviews"] = reviews.get("total_reviews", "")
        time.sleep(STORE_DELAY)
    else:
        for k in REVIEWS_COLUMNS:
            row[k] = ""

    if need_spy:
        spy = get_steamspy_data(appid)
        row["estimated_owners"] = spy.get("estimated_owners", "")
        row["avg_playtime_global"] = spy.get("avg_playtime_global", "")
        row["median_playtime_global"] = spy.get("median_playtime_global", "")
        row["steamspy_tags"] = spy.get("steamspy_tags", "")
        time.sleep(STEAMSPY_DELAY)
    else:
        for k in STEAMSPY_COLUMNS:
            row[k] = ""

    return row


# ── Helpers ────────────────────────────────────────────────────────────

def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins:02d}m"


def sort_rows(rows: list[dict], sort_key, sort_secondary=None):
    field, ascending = SORT_OPTIONS.get(sort_key, ("playtime_hours", False))

    if sort_secondary and sort_secondary in SORT_OPTIONS:
        field2, asc2 = SORT_OPTIONS[sort_secondary]
    else:
        field2, asc2 = None, False

    for row in rows:
        _add_sort_fields(row)

    def make_key(row):
        v1 = row.get(field, "")
        if v1 == "":
            v1 = -1 if not ascending else ""
        if field2:
            v2 = row.get(field2, "")
            if v2 == "":
                v2 = -1 if not asc2 else ""
            return (v1, v2)
        return (v1,)

    return sorted(rows, key=make_key, reverse=not ascending)


def build_summary(rows: list[dict]) -> str:
    total_playtime = sum(r.get("playtime_hours", 0) or 0 for r in rows)
    played = [r for r in rows if (r.get("playtime_hours", 0) or 0) > 0]
    unplayed = len(rows) - len(played)

    genre_counts: dict[str, int] = {}
    for r in rows:
        for g in str(r.get("genres", "")).split(", "):
            g = g.strip()
            if g:
                genre_counts[g] = genre_counts.get(g, 0) + 1
    top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    scores = [
        r["metacritic_score"] for r in rows
        if isinstance(r.get("metacritic_score"), (int, float))
        and r.get("metacritic_score") != ""
    ]
    avg_meta = round(sum(scores) / len(scores), 1) if scores else "N/A"

    lines = [
        f"\n{'─' * 50}",
        " Export Summary",
        f"{'─' * 50}",
        f"  Total games exported : {len(rows)}",
        f"  Played               : {len(played)}",
        f"  Unplayed             : {unplayed}",
        f"  Total playtime       : {total_playtime:,.1f} hours",
    ]
    if played:
        lines.append(
            f"  Avg playtime (played): {total_playtime / len(played):,.1f} hours"
        )
    lines.append(f"  Avg Metacritic score : {avg_meta}")
    if top_genres:
        genre_str = ", ".join(f"{g} ({c})" for g, c in top_genres)
        lines.append(f"  Top genres           : {genre_str}")
    lines.append(f"{'─' * 50}")
    return "\n".join(lines)


# ── Export pipeline ────────────────────────────────────────────────────

def run_export(cfg: dict, log_callback=None, progress_callback=None,
               cancel_event=None, selected_columns: set | None = None):
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            try:
                print(msg)
            except Exception:
                pass

    log(f"\n{'=' * 55}")
    log(" Steam Library Exporter")
    log(f"{'=' * 55}\n")

    games = get_owned_games(cfg["key"], cfg["steamid"], log_func=log)
    games.sort(key=lambda g: g.get("playtime_forever", 0), reverse=True)

    if cfg.get("limit", 0) > 0:
        games = games[: cfg["limit"]]
        log(f"[INFO] Limited to top {cfg['limit']} games by playtime.\n")

    if cfg.get("min_playtime", 0) > 0:
        before = len(games)
        min_mins = cfg["min_playtime"] * 60
        games = [g for g in games if g.get("playtime_forever", 0) >= min_mins]
        skipped = before - len(games)
        log(
            f"[INFO] Filtered to {len(games)} games with >= {cfg['min_playtime']}h "
            f"playtime (removed {skipped}).\n"
        )

    rows: list[dict] = []
    total = len(games)
    export_start = time.time()

    for i, game in enumerate(games, 1):
        if cancel_event and cancel_event.is_set():
            log("[取消] 用户中断导出")
            return None

        name = game.get("name", str(game["appid"]))
        elapsed = time.time() - export_start
        if i > 1:
            avg_per_game = elapsed / (i - 1)
            remaining = avg_per_game * (total - i + 1)
            eta_str = f"~{format_duration(remaining)}"
        else:
            eta_str = "..."

        if progress_callback:
            progress_callback(i, total, name, eta_str)

        status = f"  [{i}/{total}] {name}... | elapsed {format_duration(elapsed)}, ETA {eta_str}"
        log(status)

        row = enrich_game(
            game,
            use_steamspy=not cfg.get("no_steamspy", False),
            selected_columns=selected_columns,
            log_func=log,
        )
        rows.append(row)

    if not rows:
        log("[ERROR] No data to write.")
        return None

    if cancel_event and cancel_event.is_set():
        log("[取消] 用户中断导出")
        return None

    sort_key = cfg.get("sort", "playtime")
    sort_secondary = cfg.get("sort_secondary")
    if sort_key != "playtime" or sort_secondary:
        rows = sort_rows(rows, sort_key, sort_secondary=sort_secondary)

    fmt = cfg.get("format", "csv")
    output = cfg["output"]

    from sle.exporters import get_exporter
    exporter = get_exporter(fmt)
    exporter.export(rows, output, selected_columns=selected_columns)

    total_time = time.time() - export_start
    log(f"\n[DONE] Exported {len(rows)} games -> {output} ({format_duration(total_time)})")

    if selected_columns:
        en_fields = [k for k in ALL_COLUMNS if k in selected_columns]
    else:
        en_fields = [k for k in ALL_COLUMNS if k in rows[0]]
    cn_fields = [CN_COLUMNS.get(k, k) for k in en_fields]
    log(f"       Columns: {', '.join(cn_fields)}")

    log(build_summary(rows))

    return rows
