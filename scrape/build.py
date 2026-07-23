"""Fetch new Steam announcements, parse them deterministically, and update
data/patches.json. No manual transcription, no AI — this is the entire pipeline.

Usage:
    python scrape/build.py                # fetch, parse, write data/patches.json
    python scrape/build.py --count 200     # inspect a larger Steam news window
    python scrape/build.py --dry-run       # parse but don't write, print a summary
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parser as patch_parser  # noqa: E402
import scraper  # noqa: E402

BASE_DIR = Path(__file__).resolve().parents[1]
ROSTER_FILE = BASE_DIR / "data" / "roster.json"
PATCHES_FILE = BASE_DIR / "data" / "patches.json"


def load_roster():
    return json.loads(ROSTER_FILE.read_text(encoding="utf-8"))


def load_existing_patches():
    if not PATCHES_FILE.exists():
        return []
    return json.loads(PATCHES_FILE.read_text(encoding="utf-8"))


def write_patches_atomically(patches):
    """Temp file + os.replace so a crash mid-write never leaves a half-written file."""
    rendered = json.dumps(patches, indent=2, ensure_ascii=False) + "\n"
    tmp_path = PATCHES_FILE.with_suffix(".json.tmp")
    tmp_path.write_text(rendered, encoding="utf-8")
    os.replace(tmp_path, PATCHES_FILE)


def build(count=100, dry_run=False):
    roster = load_roster()
    new_announcements = scraper.scrape_new_announcements(count)

    if not new_announcements:
        print("No new Steam announcements found; data/patches.json is already up to date.")
        return 0

    new_entries = [
        patch_parser.parse_announcement(announcement, roster)
        for announcement in new_announcements
    ]

    existing = load_existing_patches()
    combined = sorted(new_entries + existing, key=lambda p: p["posttime"], reverse=True)

    for entry in new_entries:
        n_heroes = len(entry["heroes"])
        n_items = len(entry["items"])
        n_general = len(entry["general"])
        print(
            f"parsed {entry['headline']!r}: "
            f"{n_heroes} hero(es), {n_items} item(s), {n_general} general line(s)"
        )

    if dry_run:
        print(f"\n--dry-run: would write {len(combined)} total patch(es); nothing written.")
        return 0

    write_patches_atomically(combined)
    print(f"\nWrote data/patches.json: {len(new_entries)} new, {len(combined)} total.")
    return 0


def main():
    parser_cli = argparse.ArgumentParser(description=__doc__)
    parser_cli.add_argument(
        "--count", type=int, default=100,
        help="number of recent Steam announcements to inspect (default: 100)",
    )
    parser_cli.add_argument(
        "--dry-run", action="store_true",
        help="parse and print a summary without writing data/patches.json",
    )
    args = parser_cli.parse_args()

    if args.count < 1:
        parser_cli.error("--count must be at least 1")

    try:
        return build(count=args.count, dry_run=args.dry_run)
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
