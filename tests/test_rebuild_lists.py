import pytest
from pathlib import Path
from sf3000.rebuild_lists import (
    _display_name,
    _load_existing_keys,
    plan_rebuild,
    apply_rebuild,
)
from sf3000.rollback import RollbackManager


def test_display_name_strips_region_suffixes():
    assert _display_name("Mario Is Missing! (USA).zip") == "Mario Is Missing"


def test_display_name_strips_multiple_parens():
    assert _display_name("10-Yard Fight (Japan) (Rev 1).zip") == "10-Yard Fight"


def test_display_name_handles_underscores():
    assert _display_name("contra_hard_corps.zip") == "Contra Hard Corps"


def test_display_name_handles_plain_name():
    assert _display_name("Contra.zip") == "Contra"


def test_load_existing_keys_parses_allfiles(sd_root):
    keys = _load_existing_keys(sd_root / "cubegm" / "allfiles.lst")
    assert "FC/Super Mario Bros.zip" in keys


def test_load_existing_keys_returns_empty_for_missing_file(tmp_path):
    assert _load_existing_keys(tmp_path / "missing.lst") == set()


def test_plan_rebuild_finds_unindexed_rom(sd_root):
    (sd_root / "GBA" / "Contra.zip").write_bytes(b"rom")
    result = plan_rebuild(sd_root)
    assert "GBA" in result
    assert any(e["filename"] == "Contra.zip" for e in result["GBA"])


def test_plan_rebuild_skips_already_indexed_rom(sd_root):
    # Super Mario Bros is already in allfiles.lst
    (sd_root / "FC" / "Super Mario Bros.zip").write_bytes(b"rom")
    result = plan_rebuild(sd_root)
    fc_files = [e["filename"] for e in result.get("FC", [])]
    assert "Super Mario Bros.zip" not in fc_files


def test_plan_rebuild_skips_non_rom_files(sd_root):
    (sd_root / "GBA" / "filelist.csv").write_text("")
    result = plan_rebuild(sd_root)
    gba_files = [e["filename"] for e in result.get("GBA", [])]
    assert "filelist.csv" not in gba_files


def test_apply_rebuild_appends_to_allfiles(sd_root):
    (sd_root / "GBA" / "Contra.zip").write_bytes(b"rom")
    rollback = RollbackManager(sd_root)
    apply_rebuild(sd_root, rollback)
    content = (sd_root / "cubegm" / "allfiles.lst").read_text(encoding="utf-8")
    assert "GBA/Contra.zip" in content
    assert "Contra|CONTRA|Contra|CONTRA" in content


def test_apply_rebuild_appends_to_filelist_csv(sd_root):
    (sd_root / "GBA" / "Contra.zip").write_bytes(b"rom")
    rollback = RollbackManager(sd_root)
    apply_rebuild(sd_root, rollback)
    csv = (sd_root / "GBA" / "filelist.csv").read_text(encoding="utf-8")
    assert "Contra.zip,Contra,Contra" in csv


def test_apply_rebuild_creates_rollback_point(sd_root):
    (sd_root / "GBA" / "Contra.zip").write_bytes(b"rom")
    rollback = RollbackManager(sd_root)
    apply_rebuild(sd_root, rollback)
    assert len(rollback.list_points()) == 1
    assert rollback.list_points()[0]["command"] == "rebuild"


def test_apply_rebuild_creates_filelist_csv_if_missing(sd_root):
    (sd_root / "SFC" / "images").mkdir(exist_ok=True)
    (sd_root / "SFC" / "F-Zero.zip").write_bytes(b"rom")
    rollback = RollbackManager(sd_root)
    apply_rebuild(sd_root, rollback)
    assert (sd_root / "SFC" / "filelist.csv").exists()
