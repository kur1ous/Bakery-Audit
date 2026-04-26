from __future__ import annotations

from datetime import date, datetime
from io import BytesIO

try:
    from PIL import Image, UnidentifiedImageError
    from PIL.ExifTags import TAGS
except ImportError:  # pragma: no cover - dependency is expected in production/tests
    Image = None
    UnidentifiedImageError = Exception
    TAGS = {}


_DATETIME_FORMATS = (
    "%Y:%m:%d %H:%M:%S",
    "%Y:%m:%d %H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
)

_EXIF_DATE_TAGS = (
    "DateTimeOriginal",
    "DateTimeDigitized",
    "DateTime",
)

_INFO_DATE_KEYS = (
    "date:create",
    "date:modify",
    "creation_time",
)


def extract_reference_date(image_bytes: bytes, mime_type: str = "") -> date | None:
    if not image_bytes or Image is None:
        return None

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            exif_date = _extract_exif_date(image)
            if exif_date:
                return exif_date

            info_date = _extract_info_date(image)
            if info_date:
                return info_date
    except (OSError, UnidentifiedImageError, ValueError):
        return None

    return None


def _extract_exif_date(image: Image.Image) -> date | None:
    exif = image.getexif()
    if not exif:
        return None

    for tag_id, value in exif.items():
        tag_name = TAGS.get(tag_id, str(tag_id))
        if tag_name not in _EXIF_DATE_TAGS:
            continue
        parsed = _parse_datetime_value(value)
        if parsed:
            return parsed

    return None


def _extract_info_date(image: Image.Image) -> date | None:
    for key in _INFO_DATE_KEYS:
        parsed = _parse_datetime_value(image.info.get(key))
        if parsed:
            return parsed
    return None


def _parse_datetime_value(value: object) -> date | None:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return None

    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None
