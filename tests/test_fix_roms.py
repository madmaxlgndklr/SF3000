import shutil
import pytest
from pathlib import Path
from sf3000.fix_roms import plan_fixes, apply_fixes
from sf3000.rollback import RollbackManager


def test_plan_finds_rom_in_subfolder(sd_root):
    sub = sd_root / "GBA" / "Pokemon Emerald"
    sub.mkdir()
    (sub / "Pokemon Emerald.gba").write_bytes(b"rom")
    moves = plan_fixes(sd_root)
    assert any(m["from"] == "GBA/Pokemon Emerald/Pokemon Emerald.gba" for m in moves)
    assert any(m["to"] == "GBA/Pokemon Emerald.gba" for m in moves)


def test_plan_ignores_images_subfolder(sd_root):
    (sd_root / "GBA" / "images" / "some_cover.png").write_bytes(b"png")
    moves = plan_fixes(sd_root)
    assert not any("images" in (m.get("from") or "") for m in moves)


def test_plan_finds_rom_in_roms_folder(sd_root):
    (sd_root / "roms" / "ARES.nes").write_bytes(b"rom")
    moves = plan_fixes(sd_root)
    assert any(m["from"] == "roms/ARES.nes" and m["to"] == "FC/ARES.nes" for m in moves)


def test_plan_marks_unknown_extension_unclassified(sd_root):
    (sd_root / "roms" / "mystery.xyz").write_bytes(b"data")
    moves = plan_fixes(sd_root)
    unclassified = [m for m in moves if m["to"] is None]
    assert any("mystery.xyz" in m["from"] for m in unclassified)


def test_plan_returns_empty_when_nothing_to_fix(sd_root):
    assert plan_fixes(sd_root) == []


def test_apply_moves_file_and_creates_rollback(sd_root):
    src = sd_root / "roms" / "ARES.nes"
    src.write_bytes(b"rom")
    rollback = RollbackManager(sd_root)
    apply_fixes(sd_root, rollback)
    assert not src.exists()
    assert (sd_root / "FC" / "ARES.nes").exists()
    points = rollback.list_points()
    assert len(points) == 1
    assert points[0]["command"] == "fix-roms"


def test_apply_skips_unclassified_files(sd_root):
    mystery = sd_root / "roms" / "mystery.xyz"
    mystery.write_bytes(b"data")
    rollback = RollbackManager(sd_root)
    apply_fixes(sd_root, rollback)
    assert mystery.exists()  # not moved
