"""Use case: refine an existing figure with natural language feedback."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from src.domain.exceptions import ImageNotFoundError

if TYPE_CHECKING:
    from src.domain.interfaces import ImageGenerator


@dataclass
class EditFigureRequest:
    image_path: str
    feedback: str
    output_path: str | None = None


class EditFigureUseCase:
    def __init__(self, generator: ImageGenerator) -> None:
        self._generator = generator

    def execute(self, req: EditFigureRequest) -> dict[str, object]:
        img = Path(req.image_path)
        if not img.exists():
            raise ImageNotFoundError(f"Image not found: {req.image_path}")

        result = self._generator.edit(image_path=img, instruction=req.feedback)

        if not result.ok:
            return {
                "status": "edit_failed",
                "image_path": str(img),
                "error": result.error,
                "elapsed_seconds": result.elapsed_seconds,
            }

        save_to = Path(req.output_path) if req.output_path else img.with_stem(f"{img.stem}_edited")
        result.save(save_to)

        return {
            "status": "ok",
            "image_path": str(img),
            "output_path": str(save_to),
            "model": result.model,
            "image_size_bytes": len(result.image_bytes) if result.image_bytes else 0,
            "elapsed_seconds": result.elapsed_seconds,
            "gemini_text": result.text,
        }
