from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.application.prepare_publication_image import (
    PreparePublicationImageRequest,
    PreparePublicationImageUseCase,
)
from src.domain.exceptions import ImageNotFoundError, ValidationError

if TYPE_CHECKING:
    from pathlib import Path


class StubPublicationImageProcessor:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def prepare(
        self,
        image_path: Path,
        *,
        output_path: Path | None = None,
        target_dpi: int = 600,
        width_mm: float | None = None,
        height_mm: float | None = None,
        output_format: str | None = None,
        preserve_aspect_ratio: bool = True,
        allow_upscale: bool = True,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "image_path": image_path,
                "output_path": output_path,
                "target_dpi": target_dpi,
                "width_mm": width_mm,
                "height_mm": height_mm,
                "output_format": output_format,
                "preserve_aspect_ratio": preserve_aspect_ratio,
                "allow_upscale": allow_upscale,
            }
        )
        return {
            "output_path": str(output_path or image_path.with_name("figure_600dpi.png")),
            "output_width_px": 1417,
            "output_height_px": 945,
            "output_dpi": target_dpi,
            "resampled": True,
            "upscaled": False,
            "warnings": [],
        }


def test_prepare_publication_image_delegates_to_code_processor(tmp_path: Path) -> None:
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"fake")
    output_path = tmp_path / "prepared.tif"
    processor = StubPublicationImageProcessor()
    use_case = PreparePublicationImageUseCase(processor=processor)

    result = use_case.execute(
        PreparePublicationImageRequest(
            image_path=str(image_path),
            output_path=str(output_path),
            target_dpi=600,
            width_mm=60.0,
            output_format="tiff",
            preserve_aspect_ratio=True,
            allow_upscale=False,
        )
    )

    assert result["status"] == "ok"
    assert result["processing_route"] == "code_only_pillow"
    assert result["generation_used"] is False
    assert result["target_dpi"] == 600
    assert processor.calls == [
        {
            "image_path": image_path,
            "output_path": output_path,
            "target_dpi": 600,
            "width_mm": 60.0,
            "height_mm": None,
            "output_format": "tiff",
            "preserve_aspect_ratio": True,
            "allow_upscale": False,
        }
    ]


def test_prepare_publication_image_raises_for_missing_image(tmp_path: Path) -> None:
    use_case = PreparePublicationImageUseCase(processor=StubPublicationImageProcessor())

    with pytest.raises(ImageNotFoundError, match="Image not found"):
        use_case.execute(PreparePublicationImageRequest(image_path=str(tmp_path / "missing.png")))


def test_prepare_publication_image_raises_for_directory_path(tmp_path: Path) -> None:
    use_case = PreparePublicationImageUseCase(processor=StubPublicationImageProcessor())

    with pytest.raises(ImageNotFoundError, match="Image not found"):
        use_case.execute(PreparePublicationImageRequest(image_path=str(tmp_path)))


def test_prepare_publication_image_request_rejects_invalid_dpi() -> None:
    with pytest.raises(ValidationError, match="target_dpi"):
        PreparePublicationImageRequest(image_path="figure.png", target_dpi=0)
