import io

import pytest

from narratarr import mobilefix

Image = pytest.importorskip("PIL.Image")
pytest.importorskip("httpx")
from starlette.applications import Starlette  # noqa: E402
from starlette.responses import HTMLResponse, RedirectResponse, Response  # noqa: E402
from starlette.routing import Route  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
DESKTOP = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"


def _jpeg(size):
    out = io.BytesIO()
    Image.new("RGB", size, (90, 140, 200)).save(out, "JPEG")
    return out.getvalue()


BIG = _jpeg((3000, 3000))


def _client():
    async def index(request):
        return HTMLResponse("<html><head><title>N</title></head><body></body></html>")

    async def cover(request):
        if request.path_params["id"] == 2:
            return RedirectResponse("https://example.com/c.jpg")
        if request.path_params["id"] == 3:
            return Response(b"nope", status_code=404)
        return Response(BIG, media_type="image/jpeg")

    app = Starlette(routes=[Route("/", index), Route("/api/library/{id:int}/cover", cover)])
    mobilefix.install(app)
    return TestClient(app)


def test_phones_get_small_covers():
    r = _client().get("/api/library/1/cover", headers={"user-agent": IPHONE})
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert len(r.content) < len(BIG) // 4
    assert Image.open(io.BytesIO(r.content)).size == (480, 480)
    assert r.headers["vary"] == "User-Agent"


def test_desktops_get_the_original():
    r = _client().get("/api/library/1/cover", headers={"user-agent": DESKTOP})
    assert r.content == BIG


def test_redirects_and_errors_pass_through():
    c = _client()
    assert c.get("/api/library/2/cover", headers={"user-agent": IPHONE}, follow_redirects=False).status_code == 307
    assert c.get("/api/library/3/cover", headers={"user-agent": IPHONE}).status_code == 404


def test_page_links_the_touch_stylesheet_once():
    html = _client().get("/", headers={"user-agent": DESKTOP}).text
    assert html.count('href="/static/mobile.css" media="(hover: none)"') == 1
    assert html.count('<script src="/static/smooth.js"></script>') == 1
    assert mobilefix.add_stylesheet(mobilefix.add_stylesheet(b"<head></head>")).count(b"mobile.css") == 1


def test_phone_detection():
    assert mobilefix.is_phone(IPHONE)
    assert mobilefix.is_phone("Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 Chrome/140.0 Mobile Safari/537.36")
    assert not mobilefix.is_phone(DESKTOP)
