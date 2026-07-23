"""Fetch Steam announcements for Deadlock. Stdlib only, no API key needed.

This module only talks to Steam; it does not parse or write patches.json. See
build.py for the pipeline that turns new announcements into patch entries.
"""

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

APP_ID = 1422450
NEWS_API = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
BASE_DIR = Path(__file__).resolve().parents[1]
PATCHES_FILE = BASE_DIR / "data" / "patches.json"


def fetch_announcements(count=100):
    """Return the newest Steam news announcements using Steam's public JSON API."""
    query = urlencode({
        "appid": APP_ID,
        "count": count,
        "feeds": "steam_community_announcements",
        "maxlength": 0,
        "format": "json",
    })
    request = Request(
        f"{NEWS_API}?{query}",
        headers={"User-Agent": "Deadlock-Patch-Tracker/2.0"},
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"could not fetch Steam news: {error}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Steam returned a response that was not valid JSON") from error

    try:
        news_items = payload["appnews"]["newsitems"]
    except (KeyError, TypeError) as error:
        raise RuntimeError("Steam's news response did not contain appnews.newsitems") from error

    announcements = []
    for item in news_items:
        try:
            announcements.append({
                "gid": str(item["gid"]),
                "headline": item["title"].strip(),
                "posttime": int(item["date"]),
                "source_url": item["url"],
                "raw_body": item["contents"],
            })
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError("Steam returned an announcement with missing fields") from error

    return sorted(announcements, key=lambda item: item["posttime"], reverse=True)


def known_announcements():
    """Return headline/timestamp pairs already represented in data/patches.json."""
    try:
        patches = json.loads(PATCHES_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return set()
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{PATCHES_FILE.name} is not valid JSON: {error}") from error

    if not isinstance(patches, list):
        raise RuntimeError(f"{PATCHES_FILE.name} must contain a JSON array")
    return {
        (patch["headline"].strip(), int(patch["posttime"]))
        for patch in patches
        if (
            isinstance(patch, dict)
            and isinstance(patch.get("headline"), str)
            and "posttime" in patch
        )
    }


def scrape_new_announcements(count=100):
    """Return announcements whose headline/timestamp pair is absent from patches.json."""
    seen = known_announcements()
    return [
        item
        for item in fetch_announcements(count)
        if (item["headline"], item["posttime"]) not in seen
    ]
