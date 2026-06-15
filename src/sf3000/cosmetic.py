import shutil
from pathlib import Path
from PIL import Image
from .rollback import RollbackManager

LOGO_PATH = "xgame-logo.bmp"
BGM_PATH = "BGM/bgm.mp3"
LOGO_SIZE = (854, 480)


def apply_logo(logo_src: Path, sd_root: Path, rollback: RollbackManager) -> None:
    """Validate, convert if needed, and write new boot logo."""
    img = Image.open(logo_src)
    if img.size != LOGO_SIZE:
        raise ValueError(
            f"Logo must be {LOGO_SIZE[0]}×{LOGO_SIZE[1]} px, got {img.size[0]}×{img.size[1]}"
        )
    logo_dest = sd_root / LOGO_PATH
    tx = rollback.begin("cosmetic-logo")
    try:
        if logo_dest.exists():
            tx.backup_file(sd_root, LOGO_PATH)
        else:
            tx.record_created(LOGO_PATH)
        img.convert("RGB").save(logo_dest, "BMP")
        tx.commit()
    except Exception:
        tx.abort()
        raise


def apply_bgm(bgm_src: Path, sd_root: Path, rollback: RollbackManager) -> None:
    """Copy mp3 to BGM/bgm.mp3."""
    if bgm_src.suffix.lower() != ".mp3":
        raise ValueError(f"BGM must be an mp3 file, got {bgm_src.suffix!r}")
    bgm_dest = sd_root / BGM_PATH
    tx = rollback.begin("cosmetic-bgm")
    try:
        bgm_dest.parent.mkdir(parents=True, exist_ok=True)
        if bgm_dest.exists():
            tx.backup_file(sd_root, BGM_PATH)
        else:
            tx.record_created(BGM_PATH)
        shutil.copy2(bgm_src, bgm_dest)
        tx.commit()
    except Exception:
        tx.abort()
        raise
