import pytest
from pathlib import Path
from sf3000.unlock_systems import plan_unlock, apply_unlock, HIDDEN_SYSTEMS
from sf3000.rollback import RollbackManager


def test_plan_unlock_lists_all_hidden_systems(sd_root):
    actions = plan_unlock(sd_root)
    paths = [a["path"] for a in actions]
    for system in HIDDEN_SYSTEMS:
        assert any(system in p for p in paths)


def test_plan_unlock_empty_when_all_exist(sd_root):
    for system in HIDDEN_SYSTEMS:
        (sd_root / system).mkdir()
        (sd_root / system / "images").mkdir()
        (sd_root / system / "filelist.csv").write_text("")
    actions = plan_unlock(sd_root)
    assert actions == []


def test_apply_unlock_creates_directories(sd_root):
    rollback = RollbackManager(sd_root)
    apply_unlock(sd_root, rollback)
    for system in HIDDEN_SYSTEMS:
        assert (sd_root / system).is_dir()
        assert (sd_root / system / "images").is_dir()
        assert (sd_root / system / "filelist.csv").exists()


def test_apply_unlock_creates_rollback_point(sd_root):
    rollback = RollbackManager(sd_root)
    apply_unlock(sd_root, rollback)
    points = rollback.list_points()
    assert len(points) == 1
    assert points[0]["command"] == "unlock"


def test_apply_unlock_is_idempotent(sd_root):
    rollback = RollbackManager(sd_root)
    apply_unlock(sd_root, rollback)
    apply_unlock(sd_root, rollback)
    for system in HIDDEN_SYSTEMS:
        assert (sd_root / system).is_dir()


def test_rollback_removes_created_dirs(sd_root):
    rollback = RollbackManager(sd_root)
    apply_unlock(sd_root, rollback)
    point_name = rollback.list_points()[0]["name"]
    rollback.apply_rollback(point_name)
    for system in HIDDEN_SYSTEMS:
        assert not (sd_root / system).exists()
