# SF3000 Toolkit

A Python CLI toolkit for managing the SF3000 retro handheld gaming console — fixing ROM organisation, rebuilding game lists, fetching cover art, unlocking hidden emulators, and swapping cosmetics, all with incremental rollback.

---

## What the SF3000 is

The SF3000 is a Linux-based dual-core 1.2GHz retro handheld (Rockchip chipset, 2GB DDR3, 4.5" IPS 854×480, 3000mAh battery that doubles as a power bank). It runs a custom UI called `cubegm`/`icube` that manages 14 emulated systems and ~20,000 pre-installed games.

**The key thing to understand:** the UI does not scan your ROM folders. It reads pre-built index files (`allfiles.lst` and per-system `filelist.csv`). Dropping a ROM into the right folder is step one — updating the index is step two. This toolkit automates step two (and everything else).

---

## Supported systems

| Folder | System | Extensions |
|--------|--------|-----------|
| `FC/` | NES / Famicom | `.zip` `.nes` `.fds` |
| `SFC/` | SNES / Super Famicom | `.zip` `.sfc` `.smc` |
| `GBA/` | Game Boy Advance | `.zip` `.gba` |
| `GB/` | Game Boy | `.zip` `.gb` |
| `GBC/` | Game Boy Color | `.zip` `.gbc` |
| `MD/` | Sega Genesis / Mega Drive | `.zip` `.md` `.bin` `.gen` |
| `SMS/` | Sega Master System | `.zip` `.sms` |
| `GG/` | Sega Game Gear | `.zip` `.gg` |
| `MAME/` | Arcade (FBA / MAME2000) | `.zip` `.fba` |
| `NGPC/` | Neo Geo Pocket Color | `.zip` `.ngc` |
| `PCE/` | PC Engine / TurboGrafx-16 | `.zip` `.pce` |
| `WSC/` | WonderSwan Color | `.zip` `.wsc` |
| `ATARI/` | Atari 2600 | `.zip` `.a26` |
| `PS/` | PlayStation 1 | `.pbp` `.iso` `.img` |

**Hidden systems unlockable by this toolkit** (cores already installed, no folders yet):

| Folder | System | Extension | Core |
|--------|--------|-----------|------|
| `LYNX/` | Atari Lynx | `.lnx` | `libemu_handy.so` |
| `A7800/` | Atari 7800 | `.a78` | `libemu_prosystem.so` |
| `A5200/` | Atari 5200 | `.a52` | `libemu_a5200.so` |

---

## Installation

```bash
git clone https://github.com/madmaxlgndklr/SF3000.git
cd SF3000
pip install -e .
```

**Config file** — create `~/.config/sf3000/config.toml`:

```toml
sd_card_path = "/media/youruser/0403-0201"
thegamesdb_api_key = "YOUR_FREE_KEY"   # free at thegamesdb.net
```

---

## Commands

All commands that write to the SD card default to **dry-run mode** — they print exactly what they would do and exit. Pass `--apply` to actually make changes.

### Fix misplaced ROMs

```bash
python -m sf3000 fix-roms [--dry-run | --apply]
```

Finds ROMs inside subfolders (e.g. `GBA/SomeGame/game.gba`) and moves them up to the system root. Also moves ROMs from the unrecognised `roms/` folder to the correct system folder based on file extension.

### Rebuild game lists

```bash
python -m sf3000 rebuild [--dry-run | --apply]
```

Scans all system folders and adds any ROMs not already in `cubegm/allfiles.lst` and the system's `filelist.csv`. Never removes existing entries.

### Fetch cover art

```bash
python -m sf3000 covers [--dry-run | --apply]
```

Looks up each ROM on TheGamesDB and downloads the front boxart, resized to 320×240 PNG, into the system's `images/` folder. Skips ROMs that already have cover art.

### Unlock hidden emulators

```bash
python -m sf3000 unlock [--apply]
```

Creates `LYNX/`, `A7800/`, and `A5200/` system folders and wires up the emulator cores. Run `rebuild` afterwards once you've added ROMs.

### Cosmetic changes

```bash
python -m sf3000 cosmetic --logo PATH [--apply]   # swap boot logo (854×480 image)
python -m sf3000 cosmetic --bgm PATH  [--apply]   # set background music (mp3)
```

### Run everything

```bash
python -m sf3000 all [--dry-run | --apply]
```

Runs: `fix-roms` → `rebuild` → `covers` → `unlock` in sequence. Stops on any error.

---

## Rollback

Every `--apply` run creates a timestamped rollback point at `cubegm/.sf3000_rollback/` on the SD card before making any changes.

```bash
python -m sf3000 rollback list
# 2026-06-14T14:30:22  rebuild    (2 files modified)
# 2026-06-14T14:31:05  fix-roms   (2 files moved)
# 2026-06-14T14:32:11  covers     (47 images added)

python -m sf3000 rollback apply 2026-06-14T143022-rebuild
# Restores allfiles.lst and filelist.csv files from backup
# Rollback points are independent — undoing covers does not affect rebuild
```

---

## How game lists work (technical)

**`cubegm/allfiles.lst`** — master index read at boot, pipe-delimited:
```
FC/Super Mario Bros.zip|Super Mario Bros|SUPER MARIO BROS|超级玛丽|CJML
```
Fields: `path | display name | uppercase name | Chinese name | pinyin search key`

For ROMs you add yourself, this toolkit uses the English display name for all four fields (rather than fabricating a Chinese translation).

**`SYSTEM/filelist.csv`** — per-system shorter index, comma-delimited:
```
Super Mario Bros.zip,Super Mario Bros,超级玛丽
```

**`cubegm/cores/filelist.xml`** — overrides which emulator core runs a specific ROM (used when a game needs a non-default core).

---

## Design document

Full spec: [`docs/specs/2026-06-14-sf3000-toolkit-design.md`](docs/specs/2026-06-14-sf3000-toolkit-design.md)
