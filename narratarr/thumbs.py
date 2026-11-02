"""Small cover images for phones.

Covers saved next to audiobooks are often 2000-3000 px. A phone decodes each one into
tens of megabytes of memory, and a Library page full of them makes iOS Safari close the
tab ("A problem repeatedly occurred"). The browser asks for ?w=480 on touch devices and
gets a small JPEG instead. The original file on disk is never changed.

Pillow is optional: without it, callers fall back to the full-size cover.
"""

from __future__ import annotations

import io

MIN_WIDTH, MAX_WIDTH = 64, 1024


def clamp(width: int) -> int:
    return min(max(int(width), MIN_WIDTH), MAX_WIDTH)


def thumbnail(data: bytes, width: int) -> bytes | None:
    """A JPEG no wider than `width` (and no taller than twice that), or None to use the original."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return None
    width = clamp(width)
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.width <= width and im.height <= width * 2:
                return None  # already small: send it as it is
            im.draft("RGB", (width, width))  # JPEGs decode straight at a smaller size: fast, little memory
            img = ImageOps.exif_transpose(im)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                flat = Image.new("RGB", img.size, (0, 0, 0))
                flat.paste(img, mask=img.getchannel("A"))
                img = flat
            img = img.convert("RGB")
            img.thumbnail((width, width * 2), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            img.save(out, "JPEG", quality=82, optimize=True)
            return out.getvalue()
    except Exception:  # noqa: BLE001 - a cover we can't shrink is still a cover: send the original
        return None
