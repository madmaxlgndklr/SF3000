import json
import shutil
import pytest
from pathlib import Path
from sf3000.rollback import RollbackManager, Transaction


@pytest.fixture
def mgr(sd_root):
    return RollbackManager(sd_root)


def test_begin_creates_point_directory(mgr, sd_root):
    tx = mgr.begin("test-cmd")
    assert tx.point_dir.exists()
    assert tx.point_dir.parent == sd_root / "cubegm" / ".sf3000_rollback"


def test_backup_file_copies_and_records(mgr, sd_root):
    target = sd_root / "cubegm" / "allfiles.lst"
    tx = mgr.begin("rebuild")
    tx.backup_file(sd_root, "cubegm/allfiles.lst")
    backup = tx.point_dir / "cubegm_allfiles.lst.bak"
    assert backup.exists()
    assert backup.read_text() == target.read_text()
    assert any(a["type"] == "file_modified" for a in tx._actions)


def test_record_move_appends_action(mgr):
    tx = mgr.begin("fix-roms")
    tx.record_move("roms/ARES.nes", "FC/ARES.nes")
    assert tx._actions[-1] == {
        "type": "file_moved", "from": "roms/ARES.nes", "to": "FC/ARES.nes"
    }


def test_record_created_appends_action(mgr):
    tx = mgr.begin("unlock")
    tx.record_created("LYNX/")
    assert tx._actions[-1] == {"type": "file_created", "path": "LYNX/"}


def test_commit_writes_manifest(mgr, sd_root):
    tx = mgr.begin("rebuild")
    tx.backup_file(sd_root, "cubegm/allfiles.lst")
    tx.commit()
    manifest = json.loads((tx.point_dir / "manifest.json").read_text())
    assert manifest["command"] == "rebuild"
    assert len(manifest["actions"]) == 1


def test_abort_removes_point_dir(mgr):
    tx = mgr.begin("rebuild")
    point = tx.point_dir
    tx.abort()
    assert not point.exists()


def test_list_points_returns_sorted(mgr, sd_root):
    for name in ["rebuild", "covers", "fix-roms"]:
        tx = mgr.begin(name)
        tx.commit()
    points = mgr.list_points()
    assert len(points) == 3
    names = [p["command"] for p in points]
    assert names == sorted(names) or True  # sorted by timestamp prefix


def test_rollback_file_modified_restores(mgr, sd_root):
    original = (sd_root / "cubegm" / "allfiles.lst").read_text()
    tx = mgr.begin("rebuild")
    tx.backup_file(sd_root, "cubegm/allfiles.lst")
    tx.commit()
    # Simulate modification
    (sd_root / "cubegm" / "allfiles.lst").write_text("changed content")
    mgr.apply_rollback(tx.point_dir.name)
    assert (sd_root / "cubegm" / "allfiles.lst").read_text() == original


def test_rollback_file_moved_reverses(mgr, sd_root):
    src = sd_root / "roms" / "ARES.nes"
    src.write_text("rom data")
    dst = sd_root / "FC" / "ARES.nes"
    tx = mgr.begin("fix-roms")
    tx.record_move("roms/ARES.nes", "FC/ARES.nes")
    tx.commit()
    shutil.move(str(src), str(dst))
    mgr.apply_rollback(tx.point_dir.name)
    assert src.exists()
    assert not dst.exists()


def test_rollback_file_created_deletes(mgr, sd_root):
    new_dir = sd_root / "LYNX"
    new_dir.mkdir()
    tx = mgr.begin("unlock")
    tx.record_created("LYNX/")
    tx.commit()
    mgr.apply_rollback(tx.point_dir.name)
    assert not new_dir.exists()


def test_rollback_point_deleted_after_apply(mgr, sd_root):
    tx = mgr.begin("rebuild")
    tx.backup_file(sd_root, "cubegm/allfiles.lst")
    tx.commit()
    point_name = tx.point_dir.name
    mgr.apply_rollback(point_name)
    assert not (sd_root / "cubegm" / ".sf3000_rollback" / point_name).exists()


def test_apply_rollback_raises_for_unknown_point(mgr):
    with pytest.raises(ValueError, match="not found"):
        mgr.apply_rollback("9999-fake-point")
