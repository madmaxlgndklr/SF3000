import shutil
from pathlib import Path
from .config import SYSTEM_MAP
from .rollback import RollbackManager

_EXT_TO_SYSTEM: dict[str, str] = {
    ext: system
    for system, info in SYSTEM_MAP.items()
    for ext in info["extensions"]
}


def plan_fixes(sd_root: Path) -> list[dict]:
    """Return planned moves without executing. to=None means unclassified."""
    moves: list[dict] = []

    # ROMs inside subfolders of known system folders
    for system, info in SYSTEM_MAP.items():
        system_path = sd_root / system
        if not system_path.exists():
            continue
        for item in system_path.iterdir():
            if not item.is_dir() or item.name == "images":
                continue
            for rom in item.iterdir():
                if rom.is_file() and rom.suffix.lower() in info["extensions"]:
                    dest = system_path / rom.name
                    moves.append({
                        "from": str(rom.relative_to(sd_root)),
                        "to": str(dest.relative_to(sd_root)),
                        "reason": "subfolder",
                    })

    # ROMs in the unrecognised roms/ folder
    roms_path = sd_root / "roms"
    if roms_path.exists():
        for rom in roms_path.iterdir():
            if not rom.is_file():
                continue
            target_system = _EXT_TO_SYSTEM.get(rom.suffix.lower())
            if target_system:
                dest = sd_root / target_system / rom.name
                moves.append({
                    "from": str(rom.relative_to(sd_root)),
                    "to": str(dest.relative_to(sd_root)),
                    "reason": "roms/ folder",
                })
            else:
                moves.append({
                    "from": str(rom.relative_to(sd_root)),
                    "to": None,
                    "reason": "unclassified",
                })

    return moves


def apply_fixes(sd_root: Path, rollback: RollbackManager) -> list[dict]:
    """Execute planned moves, creating a rollback point."""
    moves = plan_fixes(sd_root)
    executable = [m for m in moves if m["to"] is not None]

    tx = rollback.begin("fix-roms")
    try:
        for move in executable:
            src = sd_root / move["from"]
            dst = sd_root / move["to"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            tx.record_move(move["from"], move["to"])
            shutil.move(str(src), str(dst))
        tx.commit()
    except Exception:
        tx.abort()
        raise

    return moves
