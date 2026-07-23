"""Flag likely roster gaps for human review.

parser.py's only failure mode that matters is silent: a hero/item name missing from
data/roster.json (new, renamed, or a rare typo like Valve's own "Vindcita") doesn't
error, it just falls into that patch's `general` list. That still leaves a telltale
shape behind: a general line written "Name: change text" where Name didn't match
anything. This script scans for that shape across data/patches.json and reports
candidates, most-repeated first, so a human can decide whether any belong in
roster.json — instead of re-reading every patch by hand.

This does NOT catch every possible mistake (see README's Known limitations: prose
announcements and missing-colon bullets leave no such trace), but it catches the
main one cheaply.

Usage:
    python scrape/review.py
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
ROSTER_FILE = BASE_DIR / "data" / "roster.json"
PATCHES_FILE = BASE_DIR / "data" / "patches.json"

# "Some Words: rest of the line" - capitalized start, short enough to plausibly be a
# proper name rather than a full sentence that happens to contain a colon.
CANDIDATE_RE = re.compile(r"^([A-Z][A-Za-z' &-]{1,32}): (.+)$")


def find_candidates(patches, known_names):
    hits = defaultdict(list)
    for patch in patches:
        for line in patch.get("general", []):
            match = CANDIDATE_RE.match(line)
            if not match:
                continue
            name = match.group(1)
            if name in known_names:
                continue
            hits[name].append((patch["headline"].strip(), line))
    return hits


def main():
    roster = json.loads(ROSTER_FILE.read_text(encoding="utf-8"))
    known_names = set(roster.get("heroes", [])) | set(roster.get("items", []))
    patches = json.loads(PATCHES_FILE.read_text(encoding="utf-8"))

    hits = find_candidates(patches, known_names)

    if not hits:
        print("No candidate roster gaps found - every 'Name: text' line in "
              "general matched a known hero/item, or there weren't any.")
        return 0

    ranked = sorted(hits.items(), key=lambda pair: len(pair[1]), reverse=True)
    print(f"{len(ranked)} candidate name(s) not in roster.json, most-repeated first:\n")
    for name, occurrences in ranked:
        print(f"{name!r} - appears {len(occurrences)} time(s)")
        headline, line = occurrences[0]
        print(f"    e.g. in {headline!r}: {line}")
        print()

    print(
        "Repeated names are the most likely real gaps (a one-off hit is more often a "
        "game mode, event label, or coincidental sentence start - see README). Add "
        "confirmed names to data/roster.json; already-parsed patches won't "
        "retroactively re-parse, so re-run build.py against a wider --count if you "
        "want history to catch up too."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
