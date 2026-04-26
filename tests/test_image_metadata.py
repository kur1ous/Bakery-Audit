from __future__ import annotations

from io import BytesIO

from PIL import Image

from src.bot.image_metadata import extract_reference_date


def test_extract_reference_date_reads_exif_original_datetime() -> None:
    image = Image.new("RGB", (4, 4), color="white")
    exif = Image.Exif()
    exif[36867] = "2026:04:24 18:30:00"

    output = BytesIO()
    image.save(output, format="JPEG", exif=exif)

    reference_date = extract_reference_date(output.getvalue(), "image/jpeg")

    assert reference_date is not None
    assert reference_date.isoformat() == "2026-04-24"


def test_extract_reference_date_returns_none_without_metadata() -> None:
    image = Image.new("RGB", (4, 4), color="white")
    output = BytesIO()
    image.save(output, format="PNG")

    assert extract_reference_date(output.getvalue(), "image/png") is None
