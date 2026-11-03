import io
from pathlib import Path

import pytest
from app.ml import InvalidImageError
from app.services.images import UploadTooLargeError, _gps_coordinate, public_url, save_image
from PIL import Image


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "blue").save(buffer, format="PNG")
    return buffer.getvalue()


def test_save_image_writes_content_addressed_path(tmp_path: Path):
    saved = save_image(io.BytesIO(_png()), "photo.png", tmp_path, 1024 * 1024)
    assert saved.path.exists()
    assert saved.path.parent.name == saved.sha256[:2]
    assert saved.path.name == f"{saved.sha256}.png"
    assert (saved.width, saved.height, saved.mime_type) == (10, 10, "image/png")
    assert public_url(saved.path, tmp_path).startswith("/files/")


def test_save_image_deduplicates_identical_bytes(tmp_path: Path):
    data = _png()
    first = save_image(io.BytesIO(data), "a.png", tmp_path, 1024 * 1024)
    second = save_image(io.BytesIO(data), "b.png", tmp_path, 1024 * 1024)
    assert first.sha256 == second.sha256
    assert first.path == second.path


def test_save_image_rejects_oversized_and_invalid_files(tmp_path: Path):
    with pytest.raises(UploadTooLargeError):
        save_image(io.BytesIO(b"x" * 100), "big.png", tmp_path, 10)
    with pytest.raises(InvalidImageError):
        save_image(io.BytesIO(b"not an image"), "bad.png", tmp_path, 1024)
    assert not list(tmp_path.glob("*.part"))


def test_malformed_gps_rationals_return_no_coordinate():
    assert _gps_coordinate(((1, 0), 0, 0), "N") is None
    assert _gps_coordinate((float("inf"), 0, 0), "N") is None
    assert _gps_coordinate((200, 0, 0), "N") is None
    assert _gps_coordinate("not a tuple", "N") is None


def test_public_url_falls_back_to_filename_outside_root(tmp_path: Path):
    outside = tmp_path / "other" / "file.jpg"
    assert public_url(outside, tmp_path / "uploads") == "/files/file.jpg"
