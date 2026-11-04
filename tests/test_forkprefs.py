import pytest

from narratarr import config, db, forkprefs, mobilefix, wanted


def rel(title, seeders=10, match=90, url=None, source="prowlarr", **kw):
    return {"title": title, "release": title, "seeders": seeders, "match": match, "usable": True,
            "language_ok": True, "url": url or f"u:{title}", "source": source, "format": "MP3", **kw}


def test_settings_default_and_save():
    assert forkprefs.load() == forkprefs.DEFAULTS
    s = forkprefs.save({"prefer_seeders": False, "preferred_words": " GraphicAudio, Full Cast ", "bogus": 1})
    assert s == {"prefer_seeders": False, "preferred_words": "GraphicAudio, Full Cast", "all_parts": True}
    assert forkprefs.load() == s
    assert (config.DATA_DIR / forkprefs.FILE).exists()


def test_most_seeders_wins_among_good_matches():
    found = [rel("A exact", seeders=3, match=100), rel("A popular", seeders=300, match=90), rel("A wrong", seeders=999, match=70)]
    order = [r["title"] for r in forkprefs.rerank(found, {**forkprefs.DEFAULTS, "preferred_words": ""})]
    assert order == ["A popular", "A exact", "A wrong"]


def test_preferred_words_win_and_ignore_spacing():
    found = [rel("Mistborn [Narrated]", seeders=500), rel("Mistborn (Graphic Audio)", seeders=4)]
    assert forkprefs.rerank(found)[0]["title"] == "Mistborn (Graphic Audio)"


def test_dead_and_unusable_releases_sink():
    found = [rel("dead GraphicAudio", seeders=0), rel("alive", seeders=2), rel("no client", seeders=900, usable=False)]
    assert forkprefs.rerank(found)[0]["title"] == "alive"


def test_part_detection():
    assert forkprefs.part_of({"release": "Sanderson - Mistborn 1 [GraphicAudio] Part 2 of 3"}) == (2, 3)
    assert forkprefs.part_of({"release": "The Final Empire (1/3) GraphicAudio"}) == (1, 3)
    assert forkprefs.part_of({"release": "Way of Kings Part 4"}) == (4, 0)
    assert forkprefs.part_of({"release": "Catch-22"}) is None
    assert forkprefs.part_of({"release": "1984 [M4B]"}) is None


def test_siblings_same_set_and_version():
    pick = rel("Final Empire [GraphicAudio] Part 1 of 3", seeders=50)
    found = [pick, rel("Final Empire [GraphicAudio] Part 2 of 3", seeders=40), rel("Final Empire Part 2 of 3", seeders=900),
             rel("Final Empire [GraphicAudio] Part 3 of 3", seeders=0), rel("Final Empire [GraphicAudio] Part 3 of 3 v2", seeders=8),
             rel("Final Empire [GraphicAudio] Part 2 of 4", seeders=99)]
    sib = forkprefs.siblings(forkprefs.rerank(found), pick, forkprefs.load())
    assert sorted(sib) == [2, 3]
    assert sib[2]["title"] == "Final Empire [GraphicAudio] Part 2 of 3"
    assert sib[3]["title"].endswith("v2")


@pytest.mark.asyncio
async def test_grab_takes_every_part(monkeypatch):
    book = db.insert({"source": "audible", "source_url": "audible:B1", "title": "The Final Empire", "author": "Brandon Sanderson",
                      "status": "wanted", "kind": "audiobook"})
    found = [rel(f"Sanderson - The Final Empire [GraphicAudio] Part {i} of 3", seeders=10 * i, url=f"r{i}") for i in (1, 2, 3)]
    grabbed = []

    async def fake_find(b):
        return [dict(f) for f in found]

    async def fake_grab(book_id, url, source_name, status="queued"):
        grabbed.append((book_id, url, status))
        db.update(book_id, status=status, release_url=url)
        return db.get(book_id)

    monkeypatch.setattr(forkprefs, "_orig_find", fake_find)
    monkeypatch.setattr(forkprefs, "_orig_grab", fake_grab)
    await forkprefs.find_releases(book)
    await forkprefs.grab(book["id"], "r1", "prowlarr", "queued")
    titles = sorted(b["title"] for b in db.list_books())
    assert titles == [f"The Final Empire (Part {i} of 3)" for i in (1, 2, 3)]
    assert sorted(u for _, u, _ in grabbed) == ["r1", "r2", "r3"]
    assert all(b["status"] == "queued" for b in db.list_books())
    await forkprefs.grab(book["id"], "r1", "prowlarr", "queued")  # again: no duplicate parts
    assert len(db.list_books()) == 3


@pytest.mark.asyncio
async def test_all_parts_off_grabs_one(monkeypatch):
    forkprefs.save({"all_parts": False})
    book = db.insert({"source": "audible", "source_url": "audible:B2", "title": "X", "author": "Y", "status": "wanted"})

    async def fake_grab(book_id, url, source_name, status="queued"):
        return db.get(book_id)

    monkeypatch.setattr(forkprefs, "_orig_grab", fake_grab)
    await forkprefs.grab(book["id"], "r1", "prowlarr")
    assert [b["title"] for b in db.list_books()] == ["X"]


def test_settings_endpoint_is_admin_only_and_saves():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    original = (wanted.find_releases, wanted.grab)
    try:
        forkprefs.install(app)
        c = TestClient(app)
        assert c.get("/api/settings/fork").json() == forkprefs.DEFAULTS
        assert c.put("/api/settings/fork", json={"prefer_seeders": False}).json()["prefer_seeders"] is False
        assert forkprefs.load()["prefer_seeders"] is False
    finally:
        wanted.find_releases, wanted.grab = original
    from narratarr import auth
    assert auth.admin_only("PUT", "/api/settings/fork") and auth.admin_only("GET", "/api/settings/fork")


def test_indexer_results_get_cover_links():
    data = {"items": [{"source": "prowlarr", "release": "Sanderson - Mistborn [M4B]", "cover_url": ""},
                      {"source": "prowlarr", "release": "Has one", "cover_url": "https://x/y.jpg"},
                      {"source": "librivox", "title": "Free", "cover_url": ""}]}
    out = mobilefix.add_indexer_covers(data)["items"]
    assert out[0]["cover_url"].startswith("/api/fork/indexer-cover?q=Sanderson%20-%20Mistborn")
    assert out[1]["cover_url"] == "https://x/y.jpg" and out[2]["cover_url"] == ""


@pytest.mark.asyncio
async def test_indexer_cover_lookup(monkeypatch):
    from narratarr import search

    async def fake_identify(q):
        return {"title": "Mistborn", "author": "Brandon Sanderson", "cover_url": "https://is1.example/cover.jpg"} if "Mistborn" in q else None

    async def no_suggestions(*a, **k):
        return []

    monkeypatch.setattr(search, "identify", fake_identify)
    monkeypatch.setattr(search, "suggestions", no_suggestions)
    assert await mobilefix.indexer_cover_url("Brandon Sanderson - Mistborn [M4B]") == "https://is1.example/cover.jpg"
    assert await mobilefix.indexer_cover_url("Unknown thing") == ""
