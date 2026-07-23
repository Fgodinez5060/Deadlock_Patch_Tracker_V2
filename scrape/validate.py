"""Check data/patches.json against data/roster.json before publishing.

    python scrape/validate.py

The site is static, so patches.json is the whole database and a bad write ships
straight to production. This catches what's easy to get wrong and invisible until the
page renders: a missing posttime, a patch out of order, a hero/item art asset that
doesn't exist, or a malformed bullet list.
"""

import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
ROSTER_FILE = BASE_DIR / "data" / "roster.json"
PATCHES_FILE = BASE_DIR / "data" / "patches.json"

VALID_PATCH_TYPES = {"balance", "hero_release", "update"}
REQUIRED_KEYS = ("headline", "patch_type", "heroes", "items", "general", "gid", "posttime")


def check_bullet_list(value, where, errors):
    if not isinstance(value, list):
        errors.append(f"{where}: expected a list, got {type(value).__name__}")
        return
    for i, entry in enumerate(value):
        if not isinstance(entry, str) or not entry.strip():
            errors.append(f"{where}[{i}]: expected a non-empty string")


def main():
    errors, warnings = [], []

    try:
        roster = json.loads(ROSTER_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL  {ROSTER_FILE} does not exist")
        return 1
    except json.JSONDecodeError as e:
        print(f"FAIL  {ROSTER_FILE.name} is not valid JSON: {e}")
        return 1

    heroes_roster = set(roster.get("heroes", []))
    items_roster = set(roster.get("items", []))

    try:
        patches = json.loads(PATCHES_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"FAIL  {PATCHES_FILE} does not exist")
        return 1
    except json.JSONDecodeError as e:
        print(f"FAIL  patches.json is not valid JSON: {e}")
        return 1

    if not isinstance(patches, list) or not patches:
        print("FAIL  patches.json must be a non-empty array")
        return 1

    for hero in sorted(heroes_roster):
        assets = (
            os.path.join("static", "heroes", f"{hero}.webp"),
            os.path.join("static", "render", f"{hero}_Render.webp"),
            os.path.join("static", "hero_name", f"{hero}_name.svg"),
        )
        for asset in assets:
            if not (BASE_DIR / asset).exists():
                errors.append(f"roster hero {hero!r}: missing {asset}")

    seen = set()
    previous_time = None

    for i, patch in enumerate(patches):
        label = f"patch[{i}] {patch.get('headline', '?')!r}"

        for key in REQUIRED_KEYS:
            if key not in patch:
                errors.append(f"{label}: missing {key!r}")
        if not isinstance(patch.get("headline"), str) or not patch.get("headline", "").strip():
            errors.append(f"{label}: headline must be a non-empty string")
        if not str(patch.get("gid", "")).isdigit():
            errors.append(f"{label}: gid must contain only digits")
        if patch.get("patch_type") not in VALID_PATCH_TYPES:
            errors.append(f"{label}: bad patch_type {patch.get('patch_type')!r}")

        try:
            posttime = int(patch["posttime"])
            if not 1_000_000_000 < posttime < 3_000_000_000:
                errors.append(f"{label}: posttime {posttime} is not a plausible unix timestamp")
            elif previous_time is not None and posttime > previous_time:
                errors.append(f"{label}: out of order - newer than the patch above it "
                              f"(patches.json must be newest first)")
            else:
                previous_time = posttime
        except (KeyError, TypeError, ValueError):
            errors.append(f"{label}: posttime {patch.get('posttime')!r} is not an integer")

        key = (patch.get("gid"), patch.get("headline"))
        if key in seen:
            errors.append(f"{label}: duplicate gid+headline - scraped twice?")
        seen.add(key)

        heroes = patch.get("heroes") or {}
        if not isinstance(heroes, dict):
            errors.append(f"{label}: heroes must be an object")
        else:
            for hero, bullets in heroes.items():
                if hero not in heroes_roster:
                    errors.append(f"{label}: unknown hero {hero!r} (not in roster.json)")
                check_bullet_list(bullets, f"{label} heroes/{hero}", errors)

        items = patch.get("items") or {}
        if not isinstance(items, dict):
            errors.append(f"{label}: items must be an object")
        else:
            for item, bullets in items.items():
                if item not in items_roster:
                    errors.append(f"{label}: unknown item {item!r} (not in roster.json)")
                check_bullet_list(bullets, f"{label} items/{item}", errors)

        check_bullet_list(patch.get("general") or [], f"{label} general", errors)

        if not heroes and not items and not patch.get("general"):
            warnings.append(f"{label}: no heroes, items, or general changes recorded")

    for warning in warnings:
        print(f"WARN  {warning}")
    for error in errors:
        print(f"FAIL  {error}")

    if errors:
        print(f"\n{len(errors)} error(s) - do not publish")
        return 1

    newest = patches[0]
    print(f"OK    {len(patches)} patches, {len(seen)} unique")
    print(f"OK    newest is {newest['headline'].strip()!r} "
          f"({len(newest.get('heroes') or {})} heroes, {len(newest.get('items') or {})} items)")
    if warnings:
        print(f"\n{len(warnings)} warning(s), but safe to publish")
    return 0


if __name__ == "__main__":
    sys.exit(main())
