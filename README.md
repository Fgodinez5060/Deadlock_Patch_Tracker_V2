# Deadlock Patch Tracker v2

A dependency-free static website that renders Deadlock patch history from
[`data/patches.json`](data/patches.json). There is no backend, no database, and no AI
anywhere in the pipeline — patch notes are scraped from Steam and split into
heroes/items/general changes with plain pattern matching against
[`data/roster.json`](data/roster.json).

## How it works

- `scrape/scraper.py` fetches recent announcements from Steam's public news JSON API
  (stdlib only, no API key).
- `scrape/parser.py` splits each announcement's BBCode body into bullets and matches
  each `Name: change text` bullet against the known hero/item names in
  `data/roster.json`. A match files the bullet under that hero/item; no match keeps it
  as a general, un-bucketed line. No ability-name extraction, no buff/nerf/fix
  classification — see the plan doc for why.
- `scrape/build.py` orchestrates the two: fetch what's new, parse it, and write
  `data/patches.json` (newest first), atomically.
- `scrape/validate.py` checks the result before it ships: valid JSON, correct
  ordering, every roster hero has its art assets, every hero/item key in
  `patches.json` is a name in `roster.json`.
- The HTML pages and `static/js/app.js` are served as flat files. On each page load,
  the browser fetches `data/patches.json` and `data/roster.json` and builds every view
  client-side.

## Keeping it updated

`.github/workflows/scrape.yml` runs `build.py` + `validate.py` on a schedule (every 6
hours) and commits `data/patches.json` if it changed — fully automatic, no manual
transcription step. To run it by hand instead:

```powershell
python scrape/build.py
python scrape/validate.py
python -m http.server 8000   # opening the HTML directly as file:// blocks the fetch
```

Then open `http://localhost:8000/`.

## Maintaining the roster

`data/roster.json` is the single source of truth for both the parser and the site.
When a new hero or item ships:

1. Add its name to `data/roster.json`.
2. For a new hero, add its art to `static/heroes/<name>.webp`,
   `static/render/<name>_Render.webp`, and `static/hero_name/<name>_name.svg`
   (`validate.py` checks these exist).
3. Re-run `python scrape/build.py` — its bullets will start routing correctly on the
   next parse. Older patches already in `data/patches.json` are not retroactively
   re-parsed.

Until the roster is updated, that hero's/item's bullets land in `general` instead of
being guessed at — a known, intentional limitation, not a bug. The same applies when
Valve **renames** an item (e.g. `Enchanter's Satchel` became `Enchanter's Emblem`
sometime before July 2026): older patches using the retired name won't retroactively
match unless that name is also added to `roster.json`.

New-item announcements are also often written as prose ("Added a new T1 Vitality Item,
Grit...") rather than a `Name: change text` bullet, so they land in `general` too even
once the item is in the roster — there's no bullet to match against yet.

## Useful commands

```powershell
python scrape/build.py --count 200   # inspect a larger Steam news window
python scrape/build.py --dry-run     # parse without writing data/patches.json
python scrape/tests/test_parser.py -v
```
