import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from sf3000.cli import main
from sf3000.config import Config


@pytest.fixture
def mock_config(sd_root):
    cfg = Config(sd_card_path=sd_root, thegamesdb_api_key="")
    with patch("sf3000.cli.Config.load", return_value=cfg):
        yield cfg


def _run(args: list[str]) -> None:
    with patch("sys.argv", ["sf3000"] + args):
        main()


def test_fix_roms_dry_run_prints_plan(mock_config, sd_root, capsys):
    (sd_root / "roms" / "ARES.nes").write_bytes(b"rom")
    _run(["fix-roms"])
    out = capsys.readouterr().out
    assert "ARES.nes" in out
    assert "Dry run" in out
    # File must NOT be moved in dry-run
    assert (sd_root / "roms" / "ARES.nes").exists()


def test_fix_roms_apply_moves_file(mock_config, sd_root):
    (sd_root / "roms" / "ARES.nes").write_bytes(b"rom")
    _run(["fix-roms", "--apply"])
    assert not (sd_root / "roms" / "ARES.nes").exists()
    assert (sd_root / "FC" / "ARES.nes").exists()


def test_rebuild_dry_run_prints_plan(mock_config, sd_root, capsys):
    (sd_root / "GBA" / "Contra.zip").write_bytes(b"rom")
    _run(["rebuild"])
    out = capsys.readouterr().out
    assert "Contra" in out
    assert "Dry run" in out


def test_rebuild_apply_writes_entries(mock_config, sd_root):
    (sd_root / "GBA" / "Contra.zip").write_bytes(b"rom")
    _run(["rebuild", "--apply"])
    content = (sd_root / "cubegm" / "allfiles.lst").read_text()
    assert "GBA/Contra.zip" in content


def test_covers_dry_run_prints_missing(mock_config, sd_root, capsys):
    (sd_root / "FC" / "filelist.csv").write_text(
        "game.zip,Some Game,Some Game\n", encoding="utf-8"
    )
    _run(["covers"])
    out = capsys.readouterr().out
    assert "Dry run" in out


def test_unlock_dry_run_prints_plan(mock_config, sd_root, capsys):
    _run(["unlock"])
    out = capsys.readouterr().out
    assert "LYNX" in out
    assert "Dry run" in out


def test_unlock_apply_creates_dirs(mock_config, sd_root):
    _run(["unlock", "--apply"])
    assert (sd_root / "LYNX").is_dir()
    assert (sd_root / "A7800").is_dir()
    assert (sd_root / "A5200").is_dir()


def test_rollback_list_shows_points(mock_config, sd_root, capsys):
    (sd_root / "roms" / "ARES.nes").write_bytes(b"rom")
    _run(["fix-roms", "--apply"])
    _run(["rollback", "list"])
    out = capsys.readouterr().out
    assert "fix-roms" in out


def test_rollback_apply_restores(mock_config, sd_root):
    (sd_root / "roms" / "ARES.nes").write_bytes(b"rom")
    _run(["fix-roms", "--apply"])
    assert (sd_root / "FC" / "ARES.nes").exists()

    # Get the rollback point name
    from sf3000.rollback import RollbackManager
    mgr = RollbackManager(sd_root)
    point_name = mgr.list_points()[0]["name"]

    _run(["rollback", "apply", point_name])
    assert (sd_root / "roms" / "ARES.nes").exists()
    assert not (sd_root / "FC" / "ARES.nes").exists()


def test_all_dry_run_runs_all_phases(mock_config, sd_root, capsys):
    (sd_root / "roms" / "ARES.nes").write_bytes(b"rom")
    (sd_root / "GBA" / "Contra.zip").write_bytes(b"rom")
    _run(["all"])
    out = capsys.readouterr().out
    assert "fix-roms" in out.lower() or "ARES" in out
    assert "rebuild" in out.lower() or "Contra" in out
    assert "unlock" in out.lower() or "LYNX" in out
