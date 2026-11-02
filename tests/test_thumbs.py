import io

import pytest

from narratarr import thumbs

Image = pytest.importorskip("PIL.Image")


def _image(fmt: str, size: tuple[int, int], mode: str = "RGB") -> bytes:
    out = io.BytesIO()
    Image.new(mode, size, (200, 120, 40) if mode == "RGB" else (200, 120, 40, 128)).save(out, fmt)
    return out.getvalue()


def test_big_cover_becomes_a_small_jpeg():
    small = thumbs.thumbnail(_image("JPEG", (3000, 3000)), 480)
    assert small is not None
    with Image.open(io.BytesIO(small)) as im:
        assert im.format == "JPEG" and im.size == (480, 480)


def test_tall_book_cover_keeps_its_shape():
    small = thumbs.thumbnail(_image("JPEG", (1600, 2560)), 480)
    with Image.open(io.BytesIO(small)) as im:
        assert im.width == 480 and im.height == 768


def test_transparent_png_is_flattened():
    small = thumbs.thumbnail(_image("PNG", (2000, 2000), "RGBA"), 300)
    with Image.open(io.BytesIO(small)) as im:
        assert im.mode == "RGB" and im.size == (300, 300)


def test_small_cover_and_junk_fall_back_to_the_original():
    assert thumbs.thumbnail(_image("JPEG", (400, 400)), 480) is None
    assert thumbs.thumbnail(b"not an image", 480) is None


def test_width_is_clamped():
    assert thumbs.clamp(5) == thumbs.MIN_WIDTH
    assert thumbs.clamp(99999) == thumbs.MAX_WIDTH
