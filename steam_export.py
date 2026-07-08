"""
Steam Library Exporter — CLI 入口
=================================
Usage:
    python steam_export.py                               # 交互模式
    python steam_export.py --key KEY --steamid ID        # 命令行模式
    python steam_export.py --key KEY --steamid ID --limit 5 --no-steamspy
"""

import argparse
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # noqa: E402

from sle.engine import run_export, __version__, AVAILABLE_LANGS, ALL_COLUMNS, CORE_COLUMNS  # noqa: E402


def _load_env_file() -> None:
    env_path = Path(__file__).parent / "config" / ".env"
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            if key not in os.environ:
                os.environ[key] = val.strip()


def prompt_choice(prompt: str, options: list[str], default: str) -> str:
    while True:
        val = input(f"  {prompt} [{'/'.join(options)}] ({default}): ").strip().lower()
        if not val:
            return default
        if val in options:
            return val
        print(f"    Invalid choice. Options: {', '.join(options)}")


def prompt_int(prompt: str, default: int) -> int:
    while True:
        val = input(f"  {prompt} ({default}): ").strip()
        if not val:
            return default
        try:
            return int(val)
        except ValueError:
            print("    Please enter a number.")


def prompt_string(prompt: str, default: str = "", required: bool = False) -> str:
    suffix = f" ({default})" if default else ""
    while True:
        val = input(f"  {prompt}{suffix}: ").strip()
        if not val and default:
            return default
        if not val and required:
            print("    This field is required.")
            continue
        if val:
            return val
        return default


def interactive_mode() -> dict:
    print(f"\n{'=' * 55}")
    print(f"  Steam Library Exporter v{__version__} — Interactive Mode")
    print(f"{'=' * 55}")
    print()
    print("  No arguments detected. Starting guided setup.")
    print("  (Tip: run with --help to see CLI flags)")
    print()

    env_key = os.environ.get("STEAM_API_KEY", "")
    env_id = os.environ.get("STEAM_ID", "")

    print("─── Credentials ───────────────────────────────────")
    if env_key:
        masked = env_key[:4] + "****" + env_key[-4:]
        print(f"  Found STEAM_API_KEY in environment: {masked}")
        use_env = input("  Use this key? [Y/n]: ").strip().lower()
        api_key = env_key if use_env != "n" else prompt_string("Steam API Key", required=True)
    else:
        print("  Get your key at: https://steamcommunity.com/dev/apikey")
        api_key = prompt_string("Steam API Key", required=True)

    print()
    if env_id:
        print(f"  Found STEAM_ID in environment: {env_id}")
        use_env = input("  Use this ID? [Y/n]: ").strip().lower()
        steam_id = env_id if use_env != "n" else prompt_string("Steam64 ID", required=True)
    else:
        print("  Find yours at: https://steamid.io")
        steam_id = prompt_string("Steam64 ID (17-digit number)", required=True)

    print()
    print("─── Export Options ────────────────────────────────")
    fmt = prompt_choice("Export format", ["csv", "json", "sqlite"], "csv")
    sort_by = prompt_choice(
        "Sort by", ["playtime", "playtime_2weeks", "name", "appid",
                    "metacritic", "reviews", "price", "release_date",
                    "owners"], "playtime",
    )
    sort2_choice = prompt_choice(
        "Secondary sort", ["none"] + ["playtime", "playtime_2weeks", "name",
        "appid", "metacritic", "reviews", "price", "release_date", "owners"],
        "none",
    )
    min_playtime = prompt_int("Min playtime in hours (0 = include all)", 0)
    limit = prompt_int("Limit to top N games (0 = all)", 0)
    use_steamspy = prompt_choice("Include SteamSpy data?", ["y", "n"], "y") == "y"

    lang_list = AVAILABLE_LANGS if AVAILABLE_LANGS else ["zh_cn"]
    lang_choice = prompt_choice("Language", lang_list, "zh_cn")

    print("\n  Columns: 'core' (4 basic cols), 'all' (24 cols), or a comma-separated list")
    cols_input = input("  Columns [core/all/list] (all): ").strip().lower()
    if cols_input == "core":
        selected_columns = CORE_COLUMNS
        print(f"    Using core columns ({len(selected_columns)}).")
    elif not cols_input or cols_input == "all":
        selected_columns = None
        print("    Using all columns.")
    else:
        selected_columns = set(
            c.strip() for c in cols_input.split(",") if c.strip() in ALL_COLUMNS
        )
        if selected_columns:
            print(f"    Using {len(selected_columns)} columns.")
        else:
            print("    No valid columns matched — using all.")
            selected_columns = None

    default_output = f"steam_library.{fmt}"
    output = prompt_string("Output filename", default=default_output)

    print()
    print("─── Review ────────────────────────────────────────")
    print(f"  Format      : {fmt.upper()}")
    print(f"  Sort        : {sort_by}")
    if min_playtime:
        print(f"  Min playtime: {min_playtime}h")
    else:
        print("  Min playtime: all games")
    if limit:
        print(f"  Limit       : top {limit}")
    else:
        print("  Limit       : all games")
    print(f"  SteamSpy    : {'yes' if use_steamspy else 'no'}")
    print(f"  Output      : {output}")
    print()

    confirm = input("  Proceed? [Y/n]: ").strip().lower()
    if confirm == "n":
        print("\n  Export cancelled.")
        sys.exit(0)

    return {
        "key": api_key,
        "steamid": steam_id,
        "output": output,
        "format": fmt,
        "sort": sort_by,
        "sort_secondary": sort2_choice if sort2_choice != "none" else None,
        "min_playtime": min_playtime,
        "limit": limit,
        "no_steamspy": not use_steamspy,
        "lang": lang_choice,
    }, selected_columns


def main():
    _load_env_file()

    if len(sys.argv) == 1:
        cfg, selected_columns = interactive_mode()
        run_export(cfg, selected_columns=selected_columns)
        return

    parser = argparse.ArgumentParser(
        description="Export Steam library to CSV or JSON",
        epilog="Run without arguments for interactive mode.",
    )
    parser.add_argument("--key", default=os.environ.get("STEAM_API_KEY", ""),
                        help="Steam Web API key")
    parser.add_argument("--steamid", default=os.environ.get("STEAM_ID", ""),
                        help="Steam64 ID")
    parser.add_argument("--output", default="",
                        help="Output file path (default: steam_library.<format>)")
    parser.add_argument("--format", choices=["csv", "json", "sqlite"], default="csv")
    parser.add_argument("--sort", choices=["playtime", "playtime_2weeks", "name",
        "appid", "metacritic", "reviews", "price", "release_date", "owners"],
        default="playtime")
    parser.add_argument("--sort-secondary", default="",
        help="Secondary sort key (default: none)")
    parser.add_argument("--min-playtime", type=float, default=0)
    parser.add_argument("--no-steamspy", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    lang_choices = AVAILABLE_LANGS if AVAILABLE_LANGS else ["zh_cn"]
    parser.add_argument("--language", choices=lang_choices, default="zh_cn",
                        help="Export language")
    parser.add_argument("--columns", default="",
                        help='Columns to export (default: all). '
                             'Shortcut "core" for basic 4 columns, '
                             'or comma-separated keys e.g. "appid,name,genres"')
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    if not args.key:
        parser.error("--key is required (or set STEAM_API_KEY in config/.env)")
    if not args.steamid:
        parser.error("--steamid is required (or set STEAM_ID in config/.env)")

    if not args.output:
        args.output = f"steam_library.{args.format}"

    if args.columns:
        if args.columns.lower() == "core":
            selected_columns = CORE_COLUMNS
        else:
            selected_columns = set(
                c.strip() for c in args.columns.split(",")
                if c.strip() in ALL_COLUMNS
            ) or None
    else:
        selected_columns = None

    cfg = {
        "key": args.key,
        "steamid": args.steamid,
        "output": args.output,
        "format": args.format,
        "sort": args.sort,
        "sort_secondary": args.sort_secondary if args.sort_secondary else None,
        "min_playtime": args.min_playtime,
        "limit": args.limit,
        "no_steamspy": args.no_steamspy,
        "lang": args.language,
    }
    run_export(cfg, selected_columns=selected_columns)


if __name__ == "__main__":
    main()
