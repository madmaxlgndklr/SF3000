# SF3000 Toolkit — Design Spec

**Date:** 2026-06-14  
**Status:** Approved

---

## Background

The SF3000 is a Linux-based dual-core 1.2GHz retro handheld (Rockchip chipset, 2GB DDR3,
4.5" IPS 854×480) running a custom UI called `cubegm`/`icube`. Its game menus are driven
by pre-built index files — it does **not** scan system folders dynamically. Adding ROMs to
the correct folder is necessary but not sufficient; the index files must also be updated or
the games will not appear.

The SD card mounts at `/media/madmaxlgndklr/0403-0201` and has the following layout:

```
<SD root>/
├── cubegm/              ← firmware + UI
│   ├── allfiles.lst     ← master game index (21,597 entries, pipe-delimited)
│   ├── favorites.lst    ← same format, user favourites
│   ├── recent.lst       ← same format, recently played
│   ├── cores/
│   │   ├── config.xml   ← core definitions + supported extensions
│   │   ├── filelist.xml ← per-ROM core overrides
│   │   ├── bios/        ← neogeo.zip, pgm.zip
│   │   └── *.so         ← 29 emulator core libraries
│   ├── saves/           ← save RAM files
│   └── states/          ← save states
├── FC/  GBA/  SFC/  MD/  GB/  GBC/  SMS/  GG/
├── MAME/  NGPC/  PCE/  WSC/  ATARI/  PS/
│   └── (each has filelist.csv + images/ subfolder)
└── BGM/  Movie/  Music/  Photo/  Ebook/
```

**allfiles.lst format:**
```
SYSTEM/filename.zip|Display Name|UPPERCASE NAME|Chinese Name|PinyinKey
```

**filelist.csv format (per system):**
```
filename.zip,Display Name,Chinese Name
```

**Known issues discovered during audit:**
- `roms/ARES.nes` and `roms/BARESARK.nes` — valid NES ROMs stranded in an unrecognised
  folder; the `roms/` directory is not mapped to any system
- `GBA/Pokemon - Emerald Version (USA, Europe)/Pokemon - Emerald Version (USA, Europe).gba`
  — ROM inside a subfolder, invisible to cubegm which only reads the flat system folder
- `GBA/rom/` — placeholder directory containing only a.txt, b.txt, c.txt
- BGM folder is empty (device supports background music)
- Cores for Atari Lynx, Atari 7800, and Atari 5200 exist as `.so` libraries but have no
  corresponding system folders or list entries

---

## Goals

Build a Python CLI toolkit (`sf3000-toolkit`) that:

1. Fixes misplaced ROMs (wrong folder, inside subfolders)
2. Rebuilds game lists so newly added ROMs appear in menus
3. Fetches missing cover art from TheGamesDB
4. Unlocks three hidden emulators (Lynx, A7800, A5200)
5. Supports cosmetic changes (boot logo, background music)
6. Provides incremental rollback for every destructive operation

---

## Architecture

### Package layout

```
SF3000/
├── README.md
├── pyproject.toml
├── src/
│   └── sf3000/
│       ├── __init__.py
│       ├── cli.py              ← entry point: python -m sf3000 <command>
│       ├── config.py           ← SD path + system/extension/core mappings
│       ├── rollback.py         ← RollbackManager + Transaction
│       ├── fix_roms.py         ← flatten subfolders, move orphaned ROMs
│       ├── rebuild_lists.py    ← allfiles.lst + per-system filelist.csv
│       ├── covers.py           ← TheGamesDB cover art fetcher
│       ├── unlock_systems.py   ← create LYNX / A7800 / A5200
│       └── cosmetic.py         ← boot logo + BGM replacement
└── docs/
    └── specs/
        └── 2026-06-14-sf3000-toolkit-design.md
```

### CLI surface

```
python -m sf3000 fix-roms   [--dry-run | --apply]
python -m sf3000 rebuild    [--dry-run | --apply]
python -m sf3000 covers     [--dry-run | --apply]
python -m sf3000 unlock     [--apply]
python -m sf3000 cosmetic   --logo PATH | --bgm PATH   [--apply]
python -m sf3000 all        [--dry-run | --apply]

python -m sf3000 rollback list
python -m sf3000 rollback apply <timestamp-command>
```

`--dry-run` is the **default** for every command that writes. `--apply` must be passed
explicitly to commit changes. `rollback` commands always apply immediately (no dry-run).

### Config

User config lives at `~/.config/sf3000/config.toml` (not in the repo, not on the SD card):

```toml
sd_card_path = "/media/madmaxlgndklr/0403-0201"
thegamesdb_api_key = "YOUR_FREE_KEY"   # free at thegamesdb.net
```

System-to-folder mappings and core assignments are hardcoded in `config.py` and match the
values observed in `cubegm/cores/config.xml`.

---

## Module Designs

### rollback.py

Every command that writes anything opens a `Transaction` before touching the SD card.

**Rollback storage:**
```
cubegm/.sf3000_rollback/
└── 2026-06-14T143022-rebuild/
    ├── manifest.json
    └── allfiles.lst.bak        ← verbatim pre-edit copy
    └── GBA_filelist.csv.bak    ← flattened name to avoid path collisions
```

**manifest.json schema:**
```json
{
  "command": "rebuild",
  "timestamp": "2026-06-14T14:30:22",
  "actions": [
    {"type": "file_modified", "path": "cubegm/allfiles.lst",
     "backup": "allfiles.lst.bak"},
    {"type": "file_modified", "path": "GBA/filelist.csv",
     "backup": "GBA_filelist.csv.bak"},
    {"type": "file_moved",    "from": "roms/ARES.nes", "to": "FC/ARES.nes"},
    {"type": "file_created",  "path": "LYNX/"}
  ]
}
```

**Rollback behaviour:**
- `file_modified` → restore from `.bak`
- `file_moved` → move back from `to` → `from`
- `file_created` → delete the path (file or directory tree)
- Rollback points are independent: undoing `covers` does not affect `rebuild`
- The rollback point directory is deleted on successful undo

### fix_roms.py

1. For each known system folder, walk one level of subdirectories. Any ROM file found
   inside a subfolder is a candidate to move up to the system root.
2. Scan `roms/` for files whose extension maps to a known system; plan a move to that
   system's folder.
3. Report any files with unrecognised extensions as "unclassified — manual placement needed".
4. Open a rollback transaction, record each move as `file_moved`, then execute.

### rebuild_lists.py

1. Open a rollback transaction; back up `cubegm/allfiles.lst` and all
   `*/filelist.csv` files.
2. Load the full set of existing `allfiles.lst` keys (the `SYSTEM/filename` prefix).
3. For each system folder, `os.listdir()` flat contents only (no recursion).
4. For each ROM file not already in the key set:
   - Derive display name: strip extension, replace `_` and `.` with spaces, title-case.
   - Generate `allfiles.lst` entry: `SYSTEM/file|Name|NAME|Name|Name`
     (English name used for all four fields — no fabricated Chinese translation).
   - Generate `filelist.csv` line: `file,Name,Name`.
5. Append new entries to both files. Never remove existing entries.

### covers.py

1. Read each system's `filelist.csv` to get display names.
2. Skip any ROM where `SYSTEM/images/<display_name>.png` already exists.
3. For each missing cover:
   - Query `GET https://api.thegamesdb.net/v1/Games/ByGameName?name=<name>&filter[platform]=<id>`
   - Pick the highest-confidence match.
   - Download the `boxart/front` image from `https://cdn.thegamesdb.net/images/original/...`
   - Resize to **320×240 px** (landscape, matches existing SD card covers) with Pillow,
     preserving aspect ratio with black letterbox padding.
   - Save as PNG to `SYSTEM/images/<display_name>.png`.
4. TheGamesDB platform IDs mapped in `config.py` (e.g. FC→NES=7, GBA=5, PS=10).
5. API key stored in `~/.config/sf3000/config.toml`; tool prints a clear error if absent.
6. Rate limiting: 1 request/second with a simple `time.sleep(1)` between calls.

### unlock_systems.py

Creates infrastructure for three emulators whose `.so` cores already exist but have no
system folders:

| Folder | Extensions | Core |
|--------|-----------|------|
| `LYNX/` | `.lnx` | `libemu_handy.so` |
| `A7800/` | `.a78` | `libemu_prosystem.so` |
| `A5200/` | `.a52` | `libemu_a5200.so` |

Steps:
1. Create `SYSTEM/` and `SYSTEM/images/` directories.
2. Create empty `SYSTEM/filelist.csv`.
3. Add `<file>` entries to `cubegm/cores/filelist.xml` for the extensions above, pointing
   to the correct core — following the existing XML format exactly.
4. All actions recorded in rollback manifest as `file_created`.

After running `unlock`, the user runs `rebuild` to populate the lists once ROMs are added.
`unlock` is idempotent — re-running it skips any folder or XML entry that already exists.

### cosmetic.py

- `--logo PATH`: Validates image is 854×480 (error if not). Converts to 24-bit BMP via
  Pillow if needed. Records backup of `xgame-logo.bmp` in rollback. Writes new file.
- `--bgm PATH`: Validates file is an mp3. Records backup of `BGM/bgm.mp3` (if present).
  Copies new file to `BGM/bgm.mp3`.

---

## Dependencies

```toml
[project]
dependencies = [
    "Pillow>=10.0",
    "requests>=2.31",
    "tomllib>=1.0",   # stdlib in Python 3.11+; tomli backport for older
]
```

No other external dependencies. No database. No local cache beyond the rollback dir.

---

## Out of Scope

- PS1 `.pbp` / `.cue` / multi-disc management (complex enough for its own spec)
- Chinese name translation (would require an external API or lookup table)
- Custom themes (`ui_*.cpd` files are binary format, not yet reverse-engineered)
- SSH/shell access to the running device OS
