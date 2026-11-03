"""The phone fix, kept in its own file so upstream releases merge in without conflicts.

Nothing in Narratarr's own files is edited. Instead, the Docker image starts Narratarr
through this module (`python -m narratarr.mobilefix`), which adds two small layers
around the normal app and then runs it exactly as `narratarr` would:

1. Covers for phones: when a phone (by its User-Agent) asks for a library cover, the
   full-size art (often 2000-3000 px) is swapped for a small JPEG made by thumbs.py.
   Desktops get the original. Files on disk are never touched.
2. Lighter styles for touch screens: the page links static/mobile.css, which only
   applies on touch devices (media="(hover: none)") and turns off the per-card blur
   effects and animations that weigh on mobile Safari.
3. Smooth refreshes, on every device: the page also loads static/smooth.js, which stops
   the 2-second library refresh from redrawing whole lists (the page flash and covers
   fading in again). Unchanged cards stay put; only changed ones are swapped.

If anything here fails, Narratarr runs as normal without it.
"""

from __future__ import annotations

import asyncio
import logging
import re

from . import thumbs

log = logging.getLogger("narratarr.mobilefix")

PHONE_WIDTH = 480
COVER_PATH = re.compile(r"/api/library/\d+/cover")
PHONE_UA = re.compile(r"iPhone|iPod|Android.*Mobile|Mobile Safari|CriOS|FxiOS|EdgiOS", re.I)
STYLESHEET = b'<link rel="stylesheet" href="/static/mobile.css" media="(hover: none)" />'
SCRIPT = b'<script src="/static/smooth.js"></script>'


def is_phone(user_agent: str) -> bool:
    return bool(PHONE_UA.search(user_agent or ""))


def add_stylesheet(html: bytes) -> bytes:
    """index.html with mobile.css and smooth.js linked just before </head> (once)."""
    if STYLESHEET in html or b"</head>" not in html:
        return html
    return html.replace(b"</head>", STYLESHEET + b"\n" + SCRIPT + b"\n</head>", 1)


async def _body(response) -> bytes:
    return b"".join([chunk async for chunk in response.body_iterator])


def _headers(response, drop: tuple[str, ...]) -> dict[str, str]:
    return {k: v for k, v in response.headers.items() if k.lower() not in drop}


def install(app) -> None:
    """Add the two layers to a Starlette/FastAPI app (before it starts serving)."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response

    async def mobile_fix(request, call_next):
        path = request.url.path
        if request.method != "GET" or not (path == "/" or COVER_PATH.fullmatch(path)):
            return await call_next(request)
        phone = is_phone(request.headers.get("user-agent", ""))
        if path != "/" and (not phone or request.query_params.get("full")):
            return await call_next(request)

        response = await call_next(request)
        kind = response.headers.get("content-type", "")
        if response.status_code != 200:
            return response
        if path == "/" and kind.startswith("text/html"):
            body = add_stylesheet(await _body(response))
            return Response(body, status_code=200, headers=_headers(response, ("content-length", "etag")))
        if path != "/" and kind.startswith("image/"):
            body = await _body(response)
            small = await asyncio.to_thread(thumbs.thumbnail, body, PHONE_WIDTH)
            headers = _headers(response, ("content-length", "content-type", "etag", "last-modified"))
            headers.update({"Cache-Control": "max-age=86400", "Vary": "User-Agent"})
            if small:
                return Response(small, status_code=200, media_type="image/jpeg", headers=headers)
            return Response(body, status_code=200, media_type=kind, headers=headers)
        return response

    app.add_middleware(BaseHTTPMiddleware, dispatch=mobile_fix)


def main() -> None:
    try:
        from . import api
        install(api.app)
    except Exception:  # noqa: BLE001 - never let the fix stop Narratarr from starting
        log.exception("Phone fix couldn't be added; starting Narratarr without it")
    from .__main__ import main as run
    run()


if __name__ == "__main__":
    main()
