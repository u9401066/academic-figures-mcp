"""Use case: refine an existing figure with natural language feedback."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from src.application.contracts import (
    ApplicationErrorCategory,
    ApplicationStatus,
    serialize_error_contract,
    serialize_generation_result_contract,
)
from src.domain.exceptions import ImageNotFoundError

if TYPE_CHECKING:
    from src.domain.interfaces import ImageGenerator, OutputFormatter


@dataclass
class EditFigureRequest:
    image_path: str
    feedback: str
    output_path: str | None = None
    output_format: str | None = None


class EditFigureUseCase:
    def __init__(
        self,
        generator: ImageGenerator,
        output_formatter: OutputFormatter | None = None,
    ) -> None:
        self._generator = generator
        self._output_formatter = output_formatter

    def execute(self, req: EditFigureRequest) -> dict[str, object]:
        img = Path(req.image_path)
        if not img.exists():
            raise ImageNotFoundError(f"Image not found: {req.image_path}")

        result = self._generator.edit(image_path=img, instruction=req.feedback)

        if not result.ok:
            payload = {
                "status": ApplicationStatus.EDIT_FAILED.value,
                "image_path": str(img),
                "error": result.error,
                "elapsed_seconds": result.elapsed_seconds,
            }
            payload.update(
                serialize_error_contract(
                    status=ApplicationStatus.EDIT_FAILED,
                    category=ApplicationErrorCategory.GENERATION_RESULT,
                )
            )
            payload.update(serialize_generation_result_contract(result))
            return payload

        if self._output_formatter is not None:
            result = self._output_formatter.convert_generation_result(result, req.output_format)

        save_to = self._resolve_output_path(
            source_path=img,
            requested_output_path=req.output_path,
            extension=result.file_extension,
        )
        result.save(save_to)

        payload = {
            "status": ApplicationStatus.OK.value,
            "image_path": str(img),
            "output_path": str(save_to),
            "output_format": req.output_format,
            "media_type": result.media_type,
            "model": result.model,
            "image_size_bytes": len(result.image_bytes) if result.image_bytes else 0,
            "elapsed_seconds": result.elapsed_seconds,
            "gemini_text": result.text,
        }
        payload.update(serialize_generation_result_contract(result))
        return payload

    @staticmethod
    def _resolve_output_path(
        *,
        source_path: Path,
        requested_output_path: str | None,
        extension: str,
    ) -> Path:
        if requested_output_path:
            target = Path(requested_output_path)
            return target if target.suffix.lower() == extension else target.with_suffix(extension)
        return source_path.with_name(f"{source_path.stem}_edited{extension}")
