import pytest
from pathlib import Path


@pytest.fixture
def sd_root(tmp_path: Path) -> Path:
    """Minimal fake SF3000 SD card structure."""
    # Standard system folders
    for system in ["FC", "GBA", "SFC", "roms"]:
        (tmp_path / system).mkdir()
        (tmp_path / system / "images").mkdir(exist_ok=True)

    # cubegm structure
    cubegm = tmp_path / "cubegm"
    cubegm.mkdir()
    (cubegm / "cores").mkdir()

    # Seed allfiles.lst with one existing entry
    (cubegm / "allfiles.lst").write_text(
        "FC/Super Mario Bros.zip|Super Mario Bros|SUPER MARIO BROS|超级玛丽|CJML\n",
        encoding="utf-8",
    )

    # Seed FC filelist.csv
    (tmp_path / "FC" / "filelist.csv").write_text(
        "Super Mario Bros.zip,Super Mario Bros,超级玛丽\n",
        encoding="utf-8",
    )

    # Empty GBA filelist.csv
    (tmp_path / "GBA" / "filelist.csv").write_text("", encoding="utf-8")

    # Minimal filelist.xml (no root element — matches real device format)
    (cubegm / "cores" / "filelist.xml").write_text(
        '<?xml version="1.0" encoding="utf-8" ?>\n',
        encoding="utf-8",
    )

    return tmp_path
