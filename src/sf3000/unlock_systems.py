from pathlib import Path
from .config import SYSTEM_MAP
from .rollback import RollbackManager

HIDDEN_SYSTEMS = ["LYNX", "A7800", "A5200"]


def plan_unlock(sd_root: Path) -> list[dict]:
    """Return list of actions needed to unlock hidden systems."""
    actions: list[dict] = []
    for system in HIDDEN_SYSTEMS:
        system_path = sd_root / system
        if not system_path.exists():
            actions.append({"type": "create_dir", "path": system})
        if not (system_path / "images").exists():
            actions.append({"type": "create_dir", "path": f"{system}/images"})
        if not (system_path / "filelist.csv").exists():
            actions.append({"type": "create_file", "path": f"{system}/filelist.csv"})
    return actions


def apply_unlock(sd_root: Path, rollback: RollbackManager) -> list[str]:
    """Create hidden system directories and empty filelist.csv files."""
    tx = rollback.begin("unlock")
    created: list[str] = []

    try:
        for system in HIDDEN_SYSTEMS:
            system_path = sd_root / system

            if not system_path.exists():
                system_path.mkdir()
                tx.record_created(system)
                created.append(f"Created {system}/")

            images_path = system_path / "images"
            if not images_path.exists():
                images_path.mkdir()
                tx.record_created(f"{system}/images")
                created.append(f"Created {system}/images/")

            csv_path = system_path / "filelist.csv"
            if not csv_path.exists():
                csv_path.write_text("", encoding="utf-8")
                tx.record_created(f"{system}/filelist.csv")
                created.append(f"Created {system}/filelist.csv")

        tx.commit()
    except Exception:
        tx.abort()
        raise

    return created
