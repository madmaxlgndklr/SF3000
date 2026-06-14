import pytest
from pathlib import Path
from unittest.mock import patch
from sf3000.config import Config, SYSTEM_MAP


def test_system_map_has_all_expected_systems():
    expected = {"FC", "SFC", "GBA", "GB", "GBC", "MD", "SMS", "GG",
                "MAME", "NGPC", "PCE", "WSC", "ATARI", "PS",
                "LYNX", "A7800", "A5200"}
    assert expected.issubset(set(SYSTEM_MAP.keys()))


def test_system_map_entries_have_required_keys():
    for system, info in SYSTEM_MAP.items():
        assert "extensions" in info, f"{system} missing extensions"
        assert isinstance(info["extensions"], list)
        assert all(e.startswith(".") for e in info["extensions"])


def test_config_load_raises_when_file_missing(tmp_path):
    with patch("sf3000.config.CONFIG_PATH", tmp_path / "nonexistent.toml"):
        with pytest.raises(FileNotFoundError, match="Config not found"):
            Config.load()


def test_config_load_reads_sd_path_and_api_key(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'sd_card_path = "/media/user/SD"\nthegamesdb_api_key = "abc123"\n',
        encoding="utf-8",
    )
    with patch("sf3000.config.CONFIG_PATH", config_file):
        cfg = Config.load()
    assert cfg.sd_card_path == Path("/media/user/SD")
    assert cfg.thegamesdb_api_key == "abc123"


def test_config_load_api_key_defaults_to_empty(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text('sd_card_path = "/media/user/SD"\n', encoding="utf-8")
    with patch("sf3000.config.CONFIG_PATH", config_file):
        cfg = Config.load()
    assert cfg.thegamesdb_api_key == ""
