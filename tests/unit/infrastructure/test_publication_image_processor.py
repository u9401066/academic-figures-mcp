from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from PIL import Image

from src.domain.exceptions import ValidationError
from src.infrastructure.publication_image_processor import PillowPublicationImageProcessor

if TYPE_CHECKING:
    from pathlib import Path


def _write_png(path: Path, *, size: tuple[int, int] = (1200, 800)) -> None:
    Image.new("RGBA", size, (30, 120, 200, 255)).save(path, format="PNG", dpi=(300, 300))


def test_prepare_publication_image_resizes_to_600_dpi_print_width(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "figure.png"
    output_path = tmp_path / "prepared.tif"
    _write_png(image_path, size=(1200, 800))
    processor = PillowPublicationImageProcessor()

    result = processor.prepare(
        image_path,
        output_path=output_path,
        target_dpi=600,
        width_mm=60.0,
        output_format="tiff",
    )

    assert result["output_path"] == str(output_path)
    assert result["output_format"] == "tiff"
    assert result["original_width_px"] == 1200
    assert result["output_width_px"] == 1417
    assert result["output_height_px"] == 945
    assert result["resampled"] is True
    assert result["upscaled"] is True
    with Image.open(output_path) as prepared:
        assert prepared.size == (1417, 945)
        assert prepared.info["dpi"] == (600.0, 600.0)


def test_prepare_publication_image_metadata_only_when_print_size_omitted(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "figure.png"
    _write_png(image_path, size=(900, 600))
    processor = PillowPublicationImageProcessor()

    result = processor.prepare(image_path, target_dpi=600, output_format="png")

    assert result["output_width_px"] == 900
    assert result["output_height_px"] == 600
    assert result["resampled"] is False
    warnings = cast("list[str]", result["warnings"])
    assert any("metadata only" in warning for warning in warnings)
    with Image.open(cast("str", result["output_path"])) as prepared:
        assert prepared.size == (900, 600)
        assert round(prepared.info["dpi"][0]) == 600


def test_prepare_publication_image_can_reject_upscaling(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    _write_png(image_path, size=(600, 400))
    processor = PillowPublicationImageProcessor()

    with pytest.raises(ValidationError, match="requires upscaling"):
        processor.prepare(
            image_path,
            target_dpi=600,
            width_mm=60.0,
            allow_upscale=False,
        )


def test_prepare_publication_image_rejects_unsupported_output_format() -> None:
    with pytest.raises(ValidationError, match="publication output_format"):
        PillowPublicationImageProcessor.normalize_output_format("gif")
