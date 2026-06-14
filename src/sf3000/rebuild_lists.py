import re
from pathlib import Path
from .config import SYSTEM_MAP
from .rollback import RollbackManager

_PARENS_RE = re.compile(r"\s*\([^)]*\)")


def _display_name(filename: str) -> str:
    """Derive a clean display name from a ROM filename."""
    stem = Path(filename).stem
    name = _PARENS_RE.sub("", stem).strip(" !.")
    name = name.replace("_", " ").replace(".", " ")
    name = " ".join(name.split())
    return name.title() if name else stem


def _load_existing_keys(allfiles_path: Path) -> set[str]:
    """Return the set of 'SYSTEM/filename' keys in allfiles.lst."""
    if not allfiles_path.exists():
        return set()
    keys: set[str] = set()
    for line in allfiles_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "|" in line:
            keys.add(line.split("|")[0])
    return keys


def plan_rebuild(sd_root: Path) -> dict[str, list[dict]]:
    """Return {system: [new_entry_dicts]} for ROMs not yet in allfiles.lst."""
    allfiles_path = sd_root / "cubegm" / "allfiles.lst"
    existing = _load_existing_keys(allfiles_path)
    new_entries: dict[str, list[dict]] = {}

    for system, info in SYSTEM_MAP.items():
        system_path = sd_root / system
        if not system_path.exists():
            continue
        system_new: list[dict] = []
        for f in sorted(system_path.iterdir()):
            if not f.is_file():
                continue
            if f.suffix.lower() not in info["extensions"]:
                continue
            key = f"{system}/{f.name}"
            if key in existing:
                continue
            name = _display_name(f.name)
            system_new.append({"key": key, "filename": f.name, "display_name": name})
        if system_new:
            new_entries[system] = system_new

    return new_entries


def apply_rebuild(sd_root: Path, rollback: RollbackManager) -> dict[str, list[dict]]:
    """Append new entries to allfiles.lst and per-system filelist.csv."""
    new_entries = plan_rebuild(sd_root)
    allfiles_path = sd_root / "cubegm" / "allfiles.lst"

    tx = rollback.begin("rebuild")
    try:
        if allfiles_path.exists():
            tx.backup_file(sd_root, "cubegm/allfiles.lst")

        allfiles_lines: list[str] = []

        for system, entries in new_entries.items():
            csv_path = sd_root / system / "filelist.csv"
            if csv_path.exists():
                tx.backup_file(sd_root, f"{system}/filelist.csv")

            csv_lines: list[str] = []
            for entry in entries:
                name = entry["display_name"]
                fname = entry["filename"]
                allfiles_lines.append(
                    f"{system}/{fname}|{name}|{name.upper()}|{name}|{name.upper()}"
                )
                csv_lines.append(f"{fname},{name},{name}")

            with open(csv_path, "a", encoding="utf-8") as fh:
                fh.write("\n".join(csv_lines) + "\n")

        with open(allfiles_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(allfiles_lines) + "\n")

        tx.commit()
    except Exception:
        tx.abort()
        raise

    return new_entries
