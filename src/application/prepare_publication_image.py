"""Use case: prepare a raster image for publication DPI requirements."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.application.contracts import ApplicationStatus
from src.domain.exceptions import ImageNotFoundError, ValidationError

if TYPE_CHECKING:
    from src.domain.interfaces import PublicationImageProcessor


@dataclass
class PreparePublicationImageRequest:
    image_path: str
    output_path: str | None = None
    target_dpi: int = 600
    width_mm: float | None = None
    height_mm: float | None = None
    output_format: str | None = None
    preserve_aspect_ratio: bool = True
    allow_upscale: bool = True

    def __post_init__(self) -> None:
        if self.target_dpi <= 0:
            raise ValidationError("target_dpi must be positive")
        if self.width_mm is not None and self.width_mm <= 0:
            raise ValidationError("width_mm must be positive when provided")
        if self.height_mm is not None and self.height_mm <= 0:
            raise ValidationError("height_mm must be positive when provided")


class PreparePublicationImageUseCase:
    def __init__(self, processor: PublicationImageProcessor) -> None:
        self._processor = processor

    def execute(self, req: PreparePublicationImageRequest) -> dict[str, Any]:
        image_path = Path(req.image_path)
        if not image_path.exists():
            raise ImageNotFoundError(f"Image not found: {req.image_path}")

        output_path = Path(req.output_path) if req.output_path else None
        result = self._processor.prepare(
            image_path,
            output_path=output_path,
            target_dpi=req.target_dpi,
            width_mm=req.width_mm,
            height_mm=req.height_mm,
            output_format=req.output_format,
            preserve_aspect_ratio=req.preserve_aspect_ratio,
            allow_upscale=req.allow_upscale,
        )

        payload: dict[str, Any] = {
            "status": ApplicationStatus.OK.value,
            "image_path": str(image_path),
            "target_dpi": req.target_dpi,
            "width_mm_requested": req.width_mm,
            "height_mm_requested": req.height_mm,
            "preserve_aspect_ratio": req.preserve_aspect_ratio,
            "allow_upscale": req.allow_upscale,
            "processing_route": "code_only_pillow",
            "generation_used": False,
        }
        payload.update(result)
        return payload
