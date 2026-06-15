import argparse
import sys
from pathlib import Path

from .config import Config
from .rollback import RollbackManager
from . import fix_roms, rebuild_lists, covers, unlock_systems, cosmetic


def _print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def cmd_fix_roms(args: argparse.Namespace, config: Config, rollback: RollbackManager) -> None:
    planned = fix_roms.plan_fixes(config.sd_card_path)
    if not planned:
        print("No misplaced ROMs found.")
        return
    for move in planned:
        if move["to"]:
            print(f"  MOVE  {move['from']}  →  {move['to']}")
        else:
            print(f"  SKIP  {move['from']}  (unclassified — move manually)")
    executable = [m for m in planned if m["to"]]
    if not args.apply:
        print(f"\nDry run — {len(executable)} moves planned. Pass --apply to execute.")
        return
    fix_roms.apply_fixes(config.sd_card_path, rollback)
    print(f"\nDone. {len(executable)} ROMs moved. Rollback point saved.")


def cmd_rebuild(args: argparse.Namespace, config: Config, rollback: RollbackManager) -> None:
    planned = rebuild_lists.plan_rebuild(config.sd_card_path)
    total = sum(len(v) for v in planned.values())
    if not total:
        print("All ROMs are already in game lists.")
        return
    for system, entries in planned.items():
        print(f"  {system}: {len(entries)} new entries")
        for e in entries:
            print(f"    + {e['display_name']}")
    if not args.apply:
        print(f"\nDry run — {total} new entries. Pass --apply to execute.")
        return
    rebuild_lists.apply_rebuild(config.sd_card_path, rollback)
    print(f"\nDone. {total} entries added. Rollback point saved.")


def cmd_covers(args: argparse.Namespace, config: Config, rollback: RollbackManager) -> None:
    missing = covers.plan_covers(config.sd_card_path)
    total = sum(len(v) for v in missing.values())
    if not total:
        print("All ROMs have cover art.")
        return
    for system, names in missing.items():
        print(f"  {system}: {len(names)} missing covers")
    if not args.apply:
        print(f"\nDry run — {total} covers to fetch. Pass --apply to execute.")
        return
    results = covers.apply_covers(config.sd_card_path, config, rollback)
    fetched = sum(results.values())
    print(f"\nDone. {fetched}/{total} covers saved. Rollback point saved.")


def cmd_unlock(args: argparse.Namespace, config: Config, rollback: RollbackManager) -> None:
    planned = unlock_systems.plan_unlock(config.sd_card_path)
    if not planned:
        print("Hidden systems already unlocked.")
        return
    for action in planned:
        print(f"  CREATE  {action['path']}")
    if not args.apply:
        print(f"\nDry run — {len(planned)} actions. Pass --apply to execute.")
        return
    created = unlock_systems.apply_unlock(config.sd_card_path, rollback)
    for item in created:
        print(f"  {item}")
    print("\nDone. Add ROMs to LYNX/, A7800/, A5200/ then run 'rebuild'. Rollback point saved.")


def cmd_cosmetic(args: argparse.Namespace, config: Config, rollback: RollbackManager) -> None:
    if not args.logo and not args.bgm:
        print("Specify --logo PATH or --bgm PATH.")
        return
    if not args.apply:
        if args.logo:
            print(f"  Would replace boot logo with: {args.logo}")
        if args.bgm:
            print(f"  Would replace background music with: {args.bgm}")
        print("Dry run — pass --apply to execute.")
        return
    if args.logo:
        cosmetic.apply_logo(Path(args.logo), config.sd_card_path, rollback)
        print("Boot logo updated. Rollback point saved.")
    if args.bgm:
        cosmetic.apply_bgm(Path(args.bgm), config.sd_card_path, rollback)
        print("Background music updated. Rollback point saved.")


def cmd_rollback_list(
    args: argparse.Namespace, config: Config, rollback: RollbackManager
) -> None:
    points = rollback.list_points()
    if not points:
        print("No rollback points found.")
        return
    for p in points:
        print(f"  {p['name']}  ({p['action_count']} actions)")


def cmd_rollback_apply(
    args: argparse.Namespace, config: Config, rollback: RollbackManager
) -> None:
    rollback.apply_rollback(args.point)
    print(f"Rolled back: {args.point}")


def cmd_all(args: argparse.Namespace, config: Config, rollback: RollbackManager) -> None:
    for title, fn in [
        ("fix-roms", cmd_fix_roms),
        ("rebuild", cmd_rebuild),
        ("covers", cmd_covers),
        ("unlock", cmd_unlock),
    ]:
        _print_header(title)
        fn(args, config, rollback)


def main() -> None:
    parser = argparse.ArgumentParser(prog="sf3000", description="SF3000 SD card toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_apply(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--apply", action="store_true", default=False,
            help="Apply changes (default is dry-run)",
        )

    # fix-roms
    p = sub.add_parser("fix-roms", help="Move misplaced ROMs to correct system folders")
    _add_apply(p)
    p.set_defaults(func=cmd_fix_roms)

    # rebuild
    p = sub.add_parser("rebuild", help="Rebuild allfiles.lst and filelist.csv for new ROMs")
    _add_apply(p)
    p.set_defaults(func=cmd_rebuild)

    # covers
    p = sub.add_parser("covers", help="Fetch missing cover art from TheGamesDB")
    _add_apply(p)
    p.set_defaults(func=cmd_covers)

    # unlock
    p = sub.add_parser("unlock", help="Create LYNX, A7800, A5200 system folders")
    _add_apply(p)
    p.set_defaults(func=cmd_unlock)

    # cosmetic
    p = sub.add_parser("cosmetic", help="Swap boot logo or background music")
    p.add_argument("--logo", metavar="PATH", help="New boot logo (854×480 image)")
    p.add_argument("--bgm", metavar="PATH", help="New background music (mp3)")
    _add_apply(p)
    p.set_defaults(func=cmd_cosmetic)

    # all
    p = sub.add_parser("all", help="Run fix-roms → rebuild → covers → unlock")
    _add_apply(p)
    p.set_defaults(func=cmd_all)

    # rollback
    p_rb = sub.add_parser("rollback", help="Manage rollback points")
    rb_sub = p_rb.add_subparsers(dest="rollback_command", required=True)

    p_list = rb_sub.add_parser("list", help="List available rollback points")
    p_list.set_defaults(func=cmd_rollback_list)

    p_apply = rb_sub.add_parser("apply", help="Apply a rollback point")
    p_apply.add_argument("point", help="Rollback point name (from 'rollback list')")
    p_apply.set_defaults(func=cmd_rollback_apply)

    args = parser.parse_args()

    try:
        config = Config.load()
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    rollback = RollbackManager(config.sd_card_path)
    args.func(args, config, rollback)
