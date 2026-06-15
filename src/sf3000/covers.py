import csv as _csv
import re
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

from .config import SYSTEM_MAP, Config
from .rollback import RollbackManager

THEGAMESDB_API = "https://api.thegamesdb.net/v1"
COVER_SIZE = (320, 240)

_BRACKET_RE = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")


def _read_filelist_csv(csv_path: Path) -> list[tuple[str, str]]:
    """Return list of (filename, display_name) from a filelist.csv."""
    if not csv_path.exists():
        return []
    entries: list[tuple[str, str]] = []
    text = csv_path.read_text(encoding="utf-8-sig", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        row = next(_csv.reader([line]))
        if len(row) > 3:
            # Unquoted comma inside filename — rsplit from right to find display name
            parts = line.rsplit(",", 2)
            if len(parts) >= 2 and parts[0].strip():
                entries.append((parts[0].strip(), parts[1].strip()))
        elif len(row) >= 2 and row[0].strip():
            entries.append((row[0].strip(), row[1].strip()))
    return entries


def _clean_search_name(name: str) -> str:
    """Strip region codes and bracket tags for TheGamesDB search."""
    return _BRACKET_RE.sub("", name).strip(" !.")


def _resize_cover(image_bytes: bytes) -> bytes:
    """Resize image to COVER_SIZE with black letterbox padding, return PNG bytes."""
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    img.thumbnail(COVER_SIZE, Image.LANCZOS)
    canvas = Image.new("RGB", COVER_SIZE, (0, 0, 0))
    x = (COVER_SIZE[0] - img.width) // 2
    y = (COVER_SIZE[1] - img.height) // 2
    canvas.paste(img, (x, y))
    buf = BytesIO()
    canvas.save(buf, "PNG")
    return buf.getvalue()


def _fetch_cover(api_key: str, game_name: str, platform_id: int) -> bytes | None:
    """Query TheGamesDB and return raw front boxart bytes, or None."""
    search_name = _clean_search_name(game_name)
    if not search_name:
        return None
    params = {
        "apikey": api_key,
        "name": search_name,
        "include": "boxart",
        "fields": "game_title",
        "filter[platform]": platform_id,
    }
    resp = requests.get(f"{THEGAMESDB_API}/Games/ByGameName", params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    games = data.get("data", {}).get("games", [])
    if not games:
        return None

    game_id = str(games[0]["id"])
    boxart_data = (
        data.get("include", {})
        .get("boxart", {})
        .get("data", {})
        .get(game_id, [])
    )
    front = next((img for img in boxart_data if img.get("side") == "front"), None)
    if not front:
        return None

    base_url = (
        data.get("include", {})
        .get("boxart", {})
        .get("base_url", {})
        .get("original", "https://cdn.thegamesdb.net/images/original/")
    )
    img_resp = requests.get(f"{base_url}{front['filename']}", timeout=30)
    img_resp.raise_for_status()
    return img_resp.content


def plan_covers(sd_root: Path) -> dict[str, list[str]]:
    """Return {system: [display_names_missing_cover_art]}."""
    missing: dict[str, list[str]] = {}
    for system, info in SYSTEM_MAP.items():
        if info.get("thegamesdb_platform_id") is None:
            continue
        system_path = sd_root / system
        if not system_path.exists():
            continue
        entries = _read_filelist_csv(system_path / "filelist.csv")
        system_missing = [
            name
            for _, name in entries
            if not (system_path / "images" / f"{name}.png").exists()
        ]
        if system_missing:
            missing[system] = system_missing
    return missing


def apply_covers(
    sd_root: Path, config: Config, rollback: RollbackManager
) -> dict[str, int]:
    """Fetch and save missing cover art. Returns {system: count_saved}."""
    if not config.thegamesdb_api_key:
        raise ValueError(
            "thegamesdb_api_key not set in ~/.config/sf3000/config.toml\n"
            "Get a free key at https://thegamesdb.net"
        )
    missing = plan_covers(sd_root)
    tx = rollback.begin("covers")
    results: dict[str, int] = {}

    try:
        for system, names in missing.items():
            platform_id = SYSTEM_MAP[system]["thegamesdb_platform_id"]
            images_dir = sd_root / system / "images"
            images_dir.mkdir(exist_ok=True)
            count = 0
            for name in names:
                try:
                    raw = _fetch_cover(config.thegamesdb_api_key, name, platform_id)
                    if raw:
                        cover_bytes = _resize_cover(raw)
                        cover_path = images_dir / f"{name}.png"
                        cover_path.write_bytes(cover_bytes)
                        tx.record_created(str(cover_path.relative_to(sd_root)))
                        count += 1
                except Exception as exc:
                    print(f"  Warning: could not fetch cover for {name!r}: {exc}")
                time.sleep(1)
            results[system] = count
        tx.commit()
    except Exception:
        tx.abort()
        raise

    return results
