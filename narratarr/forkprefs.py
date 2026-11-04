"""How this fork picks releases for Wanted books (part of the add-on fix; see mobilefix.py).

Settings live in their own file (<data dir>/fork-settings.json) and are changed under
Settings → Search & sources → Release picking. Narratarr's own files are not edited: at
startup, wanted.find_releases and wanted.grab are wrapped, so automatic searches, the
"Search now" button and "Pick a release" all follow these rules.

- Most seeders wins: among releases that clearly match the book (match >= AUTO_MATCH),
  the one with the most seeders comes first, instead of Narratarr's order (exact title,
  then free LibriVox, then M4B, then seeders).
- Preferred versions: releases whose name has one of these words ("GraphicAudio") win
  over other releases that match, whenever there is one.
- Grab every part: when the chosen release is one part of several ("Part 1 of 3"), the
  other parts are grabbed too. Each part becomes its own book ("Title (Part 2 of 3)"),
  the way GraphicAudio publishes them, so each gets its own folder.
"""

from __future__ import annotations

import json
import logging
import re
import time

from . import config, db, wanted

log = logging.getLogger("narratarr.forkprefs")

DEFAULTS = {"prefer_seeders": True, "preferred_words": "GraphicAudio", "all_parts": True}
FILE = "fork-settings.json"
_PART_OF = re.compile(r"(?i)(?:\b(?:part|pt\.?|vol(?:ume)?\.?|disc|cd)\s*)?\b(\d{1,2})\s*(?:of|/)\s*(\d{1,2})\b")
_PART = re.compile(r"(?i)\b(?:part|pt\.?)\s*(\d{1,2})\b")
_PART_SUFFIX = re.compile(r"\s*\(Part \d+(?: of \d+)?\)\s*$")
_recent: dict[int, tuple[float, list[dict]]] = {}  # book id -> (when, releases), for grabbing the other parts
_orig_find = wanted.find_releases
_orig_grab = wanted.grab


# ---- settings ---------------------------------------------------------------------------------

def load() -> dict:
    try:
        data = json.loads((config.DATA_DIR / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    return {k: type(v)(data.get(k, v)) for k, v in DEFAULTS.items()}


def save(changes: dict) -> dict:
    s = load()
    for k, v in changes.items():
        if k not in DEFAULTS:
            continue
        s[k] = bool(v) if isinstance(DEFAULTS[k], bool) else str(v or "").strip()[:300]
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    (config.DATA_DIR / FILE).write_text(json.dumps(s, indent=2), encoding="utf-8")
    return s


def words(s: dict) -> list[str]:
    """'GraphicAudio, Graphic Audio' -> ['graphicaudio'] (spaces and punctuation don't count)."""
    out = []
    for w in str(s.get("preferred_words") or "").split(","):
        w = re.sub(r"[^a-z0-9]", "", w.lower())
        if w and w not in out:
            out.append(w)
    return out


def preferred(item: dict, wanted_words: list[str]) -> bool:
    name = re.sub(r"[^a-z0-9]", "", (item.get("release") or item.get("title") or "").lower())
    return any(w in name for w in wanted_words)


def part_of(item: dict) -> tuple[int, int] | None:
    """(part, total) from 'Part 1 of 3' / '(1/3)'; (part, 0) from a bare 'Part 2'; else None."""
    name = item.get("release") or item.get("title") or ""
    m = _PART_OF.search(name)
    if m:
        k, n = int(m.group(1)), int(m.group(2))
        if 2 <= n <= 20 and 1 <= k <= n:
            return k, n
    m = _PART.search(name)
    return (int(m.group(1)), 0) if m and 1 <= int(m.group(1)) <= 20 else None


# ---- ranking ----------------------------------------------------------------------------------

def rank_key(item: dict, s: dict, wanted_words: list[str]) -> tuple:
    seeders = item.get("seeders")
    alive = seeders is None or seeders > 0
    good = item.get("match", 0) >= wanted.AUTO_MATCH
    head = (bool(item.get("usable")), bool(item.get("language_ok", True)), good,
            preferred(item, wanted_words) if good else False)
    if s["prefer_seeders"]:
        return (*head, alive, seeders if seeders is not None else 50, item.get("match", 0))
    free = item.get("source") in ("librivox", "oldtimeradio")
    m4b = (item.get("format") or "").upper() in ("M4B", "EPUB")
    return (*head, item.get("match", 0) >= 95, alive, free, m4b, seeders if seeders is not None else 50)


def rerank(found: list[dict], s: dict | None = None) -> list[dict]:
    s = s or load()
    ws = words(s)
    if s["prefer_seeders"] or ws:
        found.sort(key=lambda i: rank_key(i, s, ws), reverse=True)
    return found


async def find_releases(book: dict) -> list[dict]:
    found = rerank(await _orig_find(book))
    if book.get("id"):
        _recent[book["id"]] = (time.time(), found)
        for k in [k for k, (t, _) in _recent.items() if time.time() - t > 3600]:
            _recent.pop(k, None)
    return found


# ---- every part -------------------------------------------------------------------------------

def _good(item: dict) -> bool:
    return (item.get("usable") and item.get("language_ok", True) and item.get("match", 0) >= wanted.AUTO_MATCH
            and item.get("seeders") != 0)


def siblings(found: list[dict], pick: dict, s: dict) -> dict[int, dict]:
    """The best release for each other part of the same set as `pick`, by part number."""
    mine = part_of(pick)
    if not mine:
        return {}
    k, n = mine
    ws = words(s)
    want_pref = preferred(pick, ws)
    best: dict[int, dict] = {}
    for item in found:  # already in preference order: the first one per part wins
        p = part_of(item)
        if not p or p[0] == k or not _good(item) or preferred(item, ws) != want_pref:
            continue
        if n and p[1] and p[1] != n:
            continue  # "1 of 3" and "2 of 4" aren't the same set
        if n and p[0] > n:
            continue
        best.setdefault(p[0], item)
    return best


def _part_title(base: str, k: int, n: int) -> str:
    return f"{base} (Part {k} of {n})" if n else f"{base} (Part {k})"


async def grab(book_id: int, url: str, source_name: str, status: str = "queued") -> dict:
    book = await _orig_grab(book_id, url, source_name, status)
    try:
        await _grab_other_parts(book, url, status)
    except Exception:  # noqa: BLE001 - the main grab worked; extra parts are a bonus
        log.exception("Couldn't grab the other parts of %s", book.get("title"))
    return db.get(book_id) or book


async def _grab_other_parts(book: dict, url: str, status: str) -> None:
    s = load()
    if not s["all_parts"]:
        return
    when, found = _recent.get(book["id"], (0, []))
    if not found or not any(f.get("url") == url for f in found):
        found = await find_releases(book)
    pick = next((f for f in found if f.get("url") == url), None)
    if not pick or not part_of(pick):
        return
    k, n = part_of(pick)
    others = siblings(found, pick, s)
    if not others:
        return
    total = n or max([k, *others])
    base = _PART_SUFFIX.sub("", book["title"])
    db.update(book["id"], title=_part_title(base, k, total))
    for i, item in sorted(others.items()):
        source_url = f"{book['source_url'].split('#part')[0]}#part{i}"
        if db.get_by_url(source_url):
            continue  # already there from an earlier grab
        new = db.insert({
            "source": book.get("source") or "", "source_url": source_url, "asin": book.get("asin") or "",
            "title": _part_title(base, i, total), "author": book.get("author") or "",
            "narrators": book.get("narrators") or [], "cover_url": book.get("cover_url") or "",
            "description": book.get("description") or "", "language": book.get("language") or "",
            "series": book.get("series") or [], "released": book.get("released") or "",
            "status": "wanted", "kind": book.get("kind") or "audiobook",
            "requested_by": book.get("requested_by"),
        })
        await _orig_grab(new["id"], item["url"], item["source"], status)
        log.info("Grabbed part %s of %s for %s", i, total, base)


# ---- wiring -----------------------------------------------------------------------------------

def install(app) -> None:
    """Wrap Narratarr's release search and grab, and add the settings endpoint."""
    wanted.find_releases = find_releases
    wanted.grab = grab
    from fastapi import Body

    async def get_settings():
        return load()

    async def put_settings(body: dict = Body(...)):
        return save(body)

    # Under /api/settings/, so Narratarr's own sign-in check makes it admin-only.
    app.add_api_route("/api/settings/fork", get_settings, methods=["GET"], include_in_schema=False)
    app.add_api_route("/api/settings/fork", put_settings, methods=["PUT"], include_in_schema=False)
