"""Convert config/lang/*.toml to frontend/i18n/*.json for GitHub Pages."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC_DIR = ROOT / "config" / "lang"
DST_DIR = ROOT / "frontend" / "i18n"

DST_DIR.mkdir(parents=True, exist_ok=True)

for toml_file in sorted(SRC_DIR.glob("*.toml")):
    with open(toml_file, "rb") as f:
        data = tomllib.load(f)

    frontend_data = {
        "gui": data.get("gui", {}),
        "columns": data.get("columns", {}),
    }

    json_file = DST_DIR / f"{toml_file.stem}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(frontend_data, f, ensure_ascii=False, indent=2)

    print(f"  {toml_file.name} → {json_file.name}")

print("Done.")
