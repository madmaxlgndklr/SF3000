import pytest
from io import BytesIO
from pathlib import Path
from PIL import Image
from sf3000.cosmetic import apply_logo, apply_bgm, LOGO_SIZE
from sf3000.rollback import RollbackManager


def _make_bmp(width, height) -> bytes:
    img = Image.new("RGB", (width, height), color=(0, 128, 255))
    buf = BytesIO()
    img.save(buf, "BMP")
    return buf.getvalue()


def test_apply_logo_rejects_wrong_size(sd_root, tmp_path):
    bad_logo = tmp_path / "logo.bmp"
    bad_logo.write_bytes(_make_bmp(640, 480))
    rollback = RollbackManager(sd_root)
    with pytest.raises(ValueError, match="854×480"):
        apply_logo(bad_logo, sd_root, rollback)


def test_apply_logo_writes_bmp_to_sd(sd_root, tmp_path):
    logo = tmp_path / "logo.png"
    img = Image.new("RGB", LOGO_SIZE, color=(255, 0, 0))
    img.save(logo, "PNG")
    rollback = RollbackManager(sd_root)
    apply_logo(logo, sd_root, rollback)
    dest = sd_root / "xgame-logo.bmp"
    assert dest.exists()
    result = Image.open(dest)
    assert result.size == LOGO_SIZE


def test_apply_logo_backs_up_existing(sd_root, tmp_path):
    existing = sd_root / "xgame-logo.bmp"
    existing.write_bytes(_make_bmp(*LOGO_SIZE))
    logo = tmp_path / "logo.png"
    Image.new("RGB", LOGO_SIZE).save(logo, "PNG")
    rollback = RollbackManager(sd_root)
    apply_logo(logo, sd_root, rollback)
    points = rollback.list_points()
    assert len(points) == 1


def test_apply_logo_creates_rollback_even_without_existing(sd_root, tmp_path):
    logo = tmp_path / "logo.png"
    Image.new("RGB", LOGO_SIZE).save(logo, "PNG")
    rollback = RollbackManager(sd_root)
    apply_logo(logo, sd_root, rollback)
    assert len(rollback.list_points()) == 1


def test_apply_bgm_rejects_non_mp3(sd_root, tmp_path):
    wav = tmp_path / "music.wav"
    wav.write_bytes(b"RIFF")
    rollback = RollbackManager(sd_root)
    with pytest.raises(ValueError, match="mp3"):
        apply_bgm(wav, sd_root, rollback)


def test_apply_bgm_copies_file(sd_root, tmp_path):
    mp3 = tmp_path / "tune.mp3"
    mp3.write_bytes(b"ID3\x00fake mp3")
    rollback = RollbackManager(sd_root)
    apply_bgm(mp3, sd_root, rollback)
    assert (sd_root / "BGM" / "bgm.mp3").exists()
    assert len(rollback.list_points()) == 1


def test_apply_bgm_backs_up_existing(sd_root, tmp_path):
    bgm_dir = sd_root / "BGM"
    bgm_dir.mkdir(exist_ok=True)
    existing = bgm_dir / "bgm.mp3"
    existing.write_bytes(b"old tune")
    mp3 = tmp_path / "new.mp3"
    mp3.write_bytes(b"new tune")
    rollback = RollbackManager(sd_root)
    apply_bgm(mp3, sd_root, rollback)
    # Rollback should restore old file
    point = rollback.list_points()[0]["name"]
    rollback.apply_rollback(point)
    assert existing.read_bytes() == b"old tune"
