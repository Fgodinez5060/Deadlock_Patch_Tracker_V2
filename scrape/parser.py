"""Deterministic BBCode -> patch entry parser. No AI, no manual transcription.

Steam's patch note bodies are a flat sequence of [p]...[/p] paragraphs. Most bullets
are written "- Name: change text", where Name is either a hero or an item. This module
matches that prefix against the known roster and buckets the remainder accordingly;
anything that doesn't match a known name is kept as a general, un-bucketed line.

No attempt is made to extract ability names or classify a change as a buff/nerf/fix —
that fine-grained tagging was the most fragile part of the previous schema and is not
reproduced here.
"""

import re

PARAGRAPH_RE = re.compile(r"\[p\](.*?)\[/p\]", re.S)
TAG_RE = re.compile(r"\[/?[a-zA-Z][a-zA-Z0-9]*(?:=[^\]]*)?\]")
IMG_RE = re.compile(r"\[img[^\]]*\].*?\[/img\]", re.S)
BOLD_RE = re.compile(r"\[b\](.*?)\[/b\]", re.S)
HEADER_LABEL_RE = re.compile(r"^\\?\[\s*.+?\s*\]\\?$")


def _clean_block(raw_block):
    """Strip BBCode from one [p]...[/p] payload, returning plain text or None."""
    text = IMG_RE.sub("", raw_block)
    text = BOLD_RE.sub(r"\1", text)
    text = TAG_RE.sub("", text)
    text = text.replace(r"\[", "[").replace(r"\]", "]")
    text = text.strip()
    return text or None


def _strip_bullet(text):
    return text[2:] if text.startswith("- ") else text


def build_matcher(roster):
    """Return (regex, name -> bucket) for names in roster, longest name first."""
    heroes = roster.get("heroes", [])
    items = roster.get("items", [])
    bucket_of = {name: "heroes" for name in heroes}
    bucket_of.update({name: "items" for name in items})
    names = sorted(bucket_of, key=len, reverse=True)
    pattern = "|".join(re.escape(name) for name in names)
    regex = re.compile(rf"^({pattern}): (.*)$") if names else None
    return regex, bucket_of


def derive_patch_type(headline):
    lowered = headline.lower()
    if "hero" in lowered:
        return "hero_release"
    if "balance" in lowered:
        return "balance"
    return "update"


def parse_body(raw_body, roster):
    """Parse one Steam announcement body into {heroes, items, general}."""
    regex, bucket_of = build_matcher(roster)

    heroes = {}
    items = {}
    general = []
    buckets = {"heroes": heroes, "items": items}

    for raw_block in PARAGRAPH_RE.findall(raw_body):
        text = _clean_block(raw_block)
        if text is None or HEADER_LABEL_RE.match(text):
            continue

        line = _strip_bullet(text)
        match = regex.match(line) if regex else None
        if match:
            name, remainder = match.group(1), match.group(2)
            bucket = buckets[bucket_of[name]]
            bucket.setdefault(name, []).append(remainder)
        else:
            general.append(line)

    return {"heroes": heroes, "items": items, "general": general}


def parse_announcement(announcement, roster):
    """Parse one scraper.py announcement dict into a full patch entry."""
    body = parse_body(announcement["raw_body"], roster)
    return {
        "headline": announcement["headline"].strip(),
        "patch_type": derive_patch_type(announcement["headline"]),
        "gid": announcement["gid"],
        "posttime": announcement["posttime"],
        "heroes": body["heroes"],
        "items": body["items"],
        "general": body["general"],
    }
