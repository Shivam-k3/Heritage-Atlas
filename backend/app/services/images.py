"""Upload validation and storage. Originals are written once and never overwritten."""

import hashlib
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

from ..ml import InvalidImageError

ALLOWED_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}
CHUNK_SIZE = 1024 * 1024


class UploadTooLargeError(ValueError):
    """The upload exceeds MAX_UPLOAD_MB."""


@dataclass(frozen=True)
class SavedImage:
    path: Path
    sha256: str
    original_filename: str
    mime_type: str
    width: int
    height: int
    file_size: int
    lat: float | None
    lon: float | None
    captured_at: datetime | None = None
    exif: dict[str, str] = field(default_factory=dict)


def _rational(value: object) -> float:
    if isinstance(value, tuple) and len(value) == 2:
        return float(value[0]) / float(value[1])
    return float(value)  # type: ignore[arg-type]


def _gps_coordinate(values: object, reference: object) -> float | None:
    """Return a signed decimal coordinate, or None for malformed EXIF rationals."""
    try:
        if not isinstance(values, tuple) or len(values) != 3:
            return None
        degrees, minutes, seconds = (_rational(value) for value in values)
        coordinate = degrees + minutes / 60 + seconds / 3600
        if not isfinite(coordinate) or not -180 <= coordinate <= 180:
            return None
        if str(reference).upper() in {"S", "W"}:
            coordinate = -coordinate
        return round(coordinate, 7)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return None


def extract_gps(image: Image.Image) -> tuple[float | None, float | None]:
    try:
        exif = image.getexif()
        gps = exif.get_ifd(34853)
    except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
        return None, None
    if not gps:
        return None, None
    return _gps_coordinate(gps.get(2), gps.get(1)), _gps_coordinate(gps.get(4), gps.get(3))


EXIF_FIELDS = {
    271: "make",
    272: "model",
    306: "datetime",
    36867: "datetime_original",
    36868: "datetime_digitized",
}


def extract_captured_at(image: Image.Image) -> datetime | None:
    """EXIF DateTimeOriginal/DateTimeDigitized when present and parseable."""
    try:
        exif = image.getexif()
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    for tag in (36867, 36868, 306):
        raw = exif.get(tag)
        if not raw:
            continue
        try:
            return datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            continue
    return None


def extract_exif_metadata(image: Image.Image) -> dict[str, str]:
    """A small JSON-safe subset of EXIF. Missing values are omitted, never invented."""
    try:
        exif = image.getexif()
    except (AttributeError, KeyError, TypeError, ValueError):
        return {}
    metadata: dict[str, str] = {}
    for tag, name in EXIF_FIELDS.items():
        value = exif.get(tag)
        if value:
            metadata[name] = str(value).strip()[:200]
    lat, lon = extract_gps(image)
    if lat is not None and lon is not None:
        metadata["gps_latitude"] = str(lat)
        metadata["gps_longitude"] = str(lon)
    return metadata


def save_image(
    stream: BinaryIO, filename: str, destination_dir: Path, max_bytes: int
) -> SavedImage:
    destination_dir.mkdir(parents=True, exist_ok=True)
    original_filename = Path(filename or "upload").name[:255]
    digest = hashlib.sha256()
    size = 0
    temporary = tempfile.NamedTemporaryFile(delete=False, dir=destination_dir, suffix=".part")
    temporary_path = Path(temporary.name)
    try:
        while chunk := stream.read(CHUNK_SIZE):
            size += len(chunk)
            if size > max_bytes:
                raise UploadTooLargeError(f"upload exceeds {max_bytes // (1024 * 1024)} MB")
            digest.update(chunk)
            temporary.write(chunk)
        temporary.close()
        if size == 0:
            raise InvalidImageError("uploaded file is empty")
        sha256 = digest.hexdigest()
        try:
            with Image.open(temporary_path) as probe:
                image_format = probe.format or ""
                probe.verify()
            with Image.open(temporary_path) as image:
                width, height = image.size
                lat, lon = extract_gps(image)
                captured_at = extract_captured_at(image)
                exif = extract_exif_metadata(image)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise InvalidImageError("file is not a valid JPEG, PNG or WebP image") from exc
        if image_format not in ALLOWED_FORMATS:
            raise InvalidImageError(f"unsupported image format: {image_format or 'unknown'}")
        mime_type, extension = ALLOWED_FORMATS[image_format]
        final_path = destination_dir / sha256[:2] / f"{sha256}{extension}"
        final_path.parent.mkdir(parents=True, exist_ok=True)
        if final_path.exists():
            temporary_path.unlink(missing_ok=True)
        else:
            os.replace(temporary_path, final_path)
        return SavedImage(
            path=final_path,
            sha256=sha256,
            original_filename=original_filename,
            mime_type=mime_type,
            width=width,
            height=height,
            file_size=size,
            lat=lat,
            lon=lon,
            captured_at=captured_at,
            exif=exif,
        )
    finally:
        temporary.close()
        temporary_path.unlink(missing_ok=True)


def public_url(storage_path: str | Path, upload_root: Path) -> str:
    path = Path(storage_path)
    try:
        relative = path.resolve().relative_to(upload_root.resolve())
    except ValueError:
        relative = Path(path.name)
    return "/files/" + relative.as_posix()


def is_readable_image(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            ImageOps.exif_transpose(image).convert("RGB").load()
        return True
    except (UnidentifiedImageError, OSError, ValueError):
        return False
