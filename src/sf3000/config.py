import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "sf3000" / "config.toml"

# Ordered: stable systems first, hidden (unlockable) systems at the end.
SYSTEM_MAP: dict[str, dict] = {
    "FC":    {"extensions": [".zip", ".nes", ".fds", ".unf"],
              "core": "libemu_nes.so",        "thegamesdb_platform_id": 7},
    "SFC":   {"extensions": [".zip", ".sfc", ".smc", ".swc", ".fig"],
              "core": "libemu_sfc.so",        "thegamesdb_platform_id": 6},
    "GBA":   {"extensions": [".zip", ".gba"],
              "core": "libemu_mgba.so",       "thegamesdb_platform_id": 5},
    "GB":    {"extensions": [".zip", ".gb"],
              "core": "libemu_tgbdual.so",    "thegamesdb_platform_id": 4},
    "GBC":   {"extensions": [".zip", ".gbc"],
              "core": "libemu_tgbdual.so",    "thegamesdb_platform_id": 41},
    "MD":    {"extensions": [".zip", ".md", ".bin", ".gen", ".smd"],
              "core": "libemu_md.so",         "thegamesdb_platform_id": 36},
    "SMS":   {"extensions": [".zip", ".sms"],
              "core": "libemu_md.so",         "thegamesdb_platform_id": 35},
    "GG":    {"extensions": [".zip", ".gg"],
              "core": "libemu_md.so",         "thegamesdb_platform_id": 21},
    "MAME":  {"extensions": [".zip", ".fba"],
              "core": "libemu_fbalpha2012.so","thegamesdb_platform_id": None},
    "NGPC":  {"extensions": [".zip", ".ngc", ".ngp"],
              "core": "libemu_ngp.so",        "thegamesdb_platform_id": 48},
    "PCE":   {"extensions": [".zip", ".pce"],
              "core": "libemu_pce.so",        "thegamesdb_platform_id": 34},
    "WSC":   {"extensions": [".zip", ".wsc", ".ws"],
              "core": "libemu_wswan.so",      "thegamesdb_platform_id": 45},
    "ATARI": {"extensions": [".zip", ".a26"],
              "core": "libemu_stella.so",     "thegamesdb_platform_id": 22},
    "PS":    {"extensions": [".pbp", ".iso", ".img"],
              "core": None,                   "thegamesdb_platform_id": 10},
    # Hidden systems — cores installed on device, no folders yet.
    "LYNX":  {"extensions": [".lnx"],
              "core": "libemu_handy.so",      "thegamesdb_platform_id": 4924},
    "A7800": {"extensions": [".a78"],
              "core": "libemu_prosystem.so",  "thegamesdb_platform_id": 35},
    "A5200": {"extensions": [".a52"],
              "core": "libemu_a5200.so",      "thegamesdb_platform_id": 22},
}

# Extensions that should never be treated as ROMs
_NON_ROM_NAMES = {"filelist.csv", "images"}


@dataclass
class Config:
    sd_card_path: Path
    thegamesdb_api_key: str = ""

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(
                f"Config not found at {CONFIG_PATH}\n"
                "Create it with:\n"
                '  sd_card_path = "/media/youruser/0403-0201"\n'
                '  thegamesdb_api_key = "YOUR_FREE_KEY"  # free at thegamesdb.net'
            )
        with open(CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)
        return cls(
            sd_card_path=Path(data["sd_card_path"]),
            thegamesdb_api_key=data.get("thegamesdb_api_key", ""),
        )
