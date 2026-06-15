import pytest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image
from sf3000.covers import (
    _read_filelist_csv,
    _clean_search_name,
    _resize_cover,
    plan_covers,
    apply_covers,
    COVER_SIZE,
)
from sf3000.config import Config
from sf3000.rollback import RollbackManager


def _make_png(width=300, height=400) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_read_filelist_csv_returns_name_pairs(sd_root):
    entries = _read_filelist_csv(sd_root / "FC" / "filelist.csv")
    assert ("Super Mario Bros.zip", "Super Mario Bros") in entries


def test_read_filelist_csv_handles_bom(tmp_path):
    csv = tmp_path / "filelist.csv"
    csv.write_bytes(b"\xef\xbb\xbfgame.zip,Game Name,Chinese\n")
    entries = _read_filelist_csv(csv)
    assert entries[0] == ("game.zip", "Game Name")


def test_read_filelist_csv_returns_empty_for_missing(tmp_path):
    assert _read_filelist_csv(tmp_path / "nope.csv") == []


def test_read_filelist_csv_comma_in_filename(tmp_path):
    # Filename contains comma (e.g. "(USA, Europe)") — not quoted in original CSV
    csv = tmp_path / "filelist.csv"
    csv.write_text(
        "Pokemon - Emerald Version (USA, Europe).gba,Pokemon - Emerald Version,Pokemon - Emerald Version\n",
        encoding="utf-8",
    )
    entries = _read_filelist_csv(csv)
    assert entries[0] == (
        "Pokemon - Emerald Version (USA, Europe).gba",
        "Pokemon - Emerald Version",
    )


def test_read_filelist_csv_quoted_comma_in_display_name(tmp_path):
    # Both filename and display name contain commas — quoted per CSV spec
    csv = tmp_path / "filelist.csv"
    csv.write_text(
        '"Adventures of Batman & Robin, The (JUE).zip",'
        '"Adventures of Batman & Robin, The (JUE)",'
        '"Adventures of Batman & Robin"\n',
        encoding="utf-8",
    )
    entries = _read_filelist_csv(csv)
    assert entries[0] == (
        "Adventures of Batman & Robin, The (JUE).zip",
        "Adventures of Batman & Robin, The (JUE)",
    )


def test_clean_search_name_strips_region_codes():
    assert _clean_search_name("Sonic the Hedgehog 2 (JUE)") == "Sonic the Hedgehog 2"
    assert _clean_search_name("Double Dragon (UE) [!]") == "Double Dragon"
    assert _clean_search_name("Pokemon - Emerald Version") == "Pokemon - Emerald Version"


def test_clean_search_name_strips_japan_suffix():
    assert _clean_search_name("kung fu, the (japan)") == "kung fu, the"


def test_resize_cover_produces_exact_size():
    raw = _make_png(300, 400)
    result = _resize_cover(raw)
    img = Image.open(BytesIO(result))
    assert img.size == COVER_SIZE


def test_resize_cover_letterboxes_wide_image():
    raw = _make_png(1000, 200)
    result = _resize_cover(raw)
    img = Image.open(BytesIO(result))
    assert img.size == COVER_SIZE


def test_plan_covers_lists_missing(sd_root):
    (sd_root / "FC" / "filelist.csv").write_text(
        "game.zip,Some Game,Some Game\n", encoding="utf-8"
    )
    # No image file created → should be in plan
    missing = plan_covers(sd_root)
    assert "FC" in missing
    assert "Some Game" in missing["FC"]


def test_plan_covers_skips_existing(sd_root):
    (sd_root / "FC" / "filelist.csv").write_text(
        "game.zip,Some Game,Some Game\n", encoding="utf-8"
    )
    (sd_root / "FC" / "images" / "Some Game.png").write_bytes(b"png")
    missing = plan_covers(sd_root)
    assert "Some Game" not in missing.get("FC", [])


def test_plan_covers_skips_mame(sd_root):
    (sd_root / "MAME").mkdir(exist_ok=True)
    (sd_root / "MAME" / "filelist.csv").write_text(
        "kof97.fba,KOF 97,拳皇97\n", encoding="utf-8"
    )
    missing = plan_covers(sd_root)
    assert "MAME" not in missing


def test_apply_covers_raises_without_api_key(sd_root):
    cfg = Config(sd_card_path=sd_root, thegamesdb_api_key="")
    rollback = RollbackManager(sd_root)
    with pytest.raises(ValueError, match="thegamesdb_api_key"):
        apply_covers(sd_root, cfg, rollback)


def test_apply_covers_writes_png_and_records_created(sd_root):
    (sd_root / "FC" / "filelist.csv").write_text(
        "game.zip,Some Game,Some Game\n", encoding="utf-8"
    )
    cfg = Config(sd_card_path=sd_root, thegamesdb_api_key="testkey")
    rollback = RollbackManager(sd_root)

    fake_response = {
        "data": {"games": [{"id": 42}]},
        "include": {
            "boxart": {
                "base_url": {"original": "https://cdn.example.com/"},
                "data": {
                    "42": [{"side": "front", "filename": "art/42-1.jpg"}]
                },
            }
        },
    }

    with patch("sf3000.covers.requests.get") as mock_get:
        search_resp = MagicMock()
        search_resp.json.return_value = fake_response
        search_resp.raise_for_status = MagicMock()

        img_resp = MagicMock()
        img_resp.content = _make_png()
        img_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [search_resp, img_resp]

        with patch("sf3000.covers.time.sleep"):
            results = apply_covers(sd_root, cfg, rollback)

    assert results.get("FC", 0) == 1
    assert (sd_root / "FC" / "images" / "Some Game.png").exists()
    assert len(rollback.list_points()) == 1
