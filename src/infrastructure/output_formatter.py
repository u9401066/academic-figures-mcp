"""Infrastructure output formatter backed by Pillow."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, ClassVar

from PIL import Image, UnidentifiedImageError

from src.domain.entities import GenerationResult
from src.domain.exceptions import ValidationError
from src.domain.interfaces import OutputFormatter

if TYPE_CHECKING:
    from pathlib import Path


class PillowOutputFormatter(OutputFormatter):
    _OUTPUT_FORMAT_TO_MEDIA_TYPE: ClassVar[dict[str, str]] = {
        "png": "image/png",
        "gif": "image/gif",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "svg": "image/svg+xml",
    }
    _RASTER_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"png", "gif", "jpeg", "webp"}
    )

    def normalize_output_format(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized not in self._OUTPUT_FORMAT_TO_MEDIA_TYPE:
            supported = ", ".join(sorted(self._OUTPUT_FORMAT_TO_MEDIA_TYPE))
            raise ValidationError(f"output_format must be one of: {supported}")
        return "jpeg" if normalized == "jpg" else normalized

    def media_type_for_output_format(self, output_format: str) -> str:
        normalized = self.normalize_output_format(output_format)
        if normalized is None:
            raise ValidationError("output_format is required")
        return self._OUTPUT_FORMAT_TO_MEDIA_TYPE[normalized]

    def convert_generation_result(
        self,
        result: GenerationResult,
        output_format: str | None,
    ) -> GenerationResult:
        normalized = self.normalize_output_format(output_format)
        if normalized is None or not result.ok:
            return result

        target_media_type = self.media_type_for_output_format(normalized)
        if result.media_type == target_media_type:
            return result
        if normalized == "svg" or result.media_type == "image/svg+xml":
            raise ValidationError(
                "SVG conversion is not supported automatically; keep svg as-is or "
                "request png/gif/jpeg/webp from raster outputs."
            )
        if result.image_bytes is None:
            return result

        converted_bytes = self._convert_raster_bytes(
            image_bytes=result.image_bytes,
            output_format=normalized,
        )
        return GenerationResult(
            image_bytes=converted_bytes,
            text=result.text,
            model=result.model,
            elapsed_seconds=result.elapsed_seconds,
            error=result.error,
            media_type=target_media_type,
        )

    def convert_file(self, path: Path, output_format: str | None) -> Path:
        normalized = self.normalize_output_format(output_format)
        if normalized is None:
            return path

        current_format = self.normalize_output_format(path.suffix[1:]) if path.suffix else None
        if current_format == normalized:
            return path
        if normalized == "svg" or current_format == "svg":
            raise ValidationError(
                "SVG conversion is not supported automatically; keep svg as-is or "
                "request png/gif/jpeg/webp from raster outputs."
            )

        image_bytes = path.read_bytes()
        converted_bytes = self._convert_raster_bytes(
            image_bytes=image_bytes,
            output_format=normalized,
        )
        target_path = path.with_suffix(self._extension_for_output_format(normalized))
        target_path.write_bytes(converted_bytes)
        if target_path != path and path.exists():
            path.unlink()
        return target_path

    def _convert_raster_bytes(self, *, image_bytes: bytes, output_format: str) -> bytes:
        if output_format not in self._RASTER_OUTPUT_FORMATS:
            raise ValidationError(
                "Automatic conversion currently supports png, gif, jpeg, and webp outputs only"
            )

        try:
            with Image.open(BytesIO(image_bytes)) as image:
                converted_image = self._prepare_image_for_format(
                    image=image,
                    output_format=output_format,
                )
                save_format = output_format.upper() if output_format != "jpeg" else "JPEG"
                buffer = BytesIO()
                save_kwargs: dict[str, object] = {}
                if output_format in {"jpeg", "webp"}:
                    save_kwargs["quality"] = 95
                converted_image.save(buffer, format=save_format, **save_kwargs)
        except UnidentifiedImageError as exc:
            raise ValidationError(
                "Image conversion failed because the provider output is not a "
                "readable raster image"
            ) from exc

        return buffer.getvalue()

    @staticmethod
    def _prepare_image_for_format(*, image: Image.Image, output_format: str) -> Image.Image:
        if output_format == "jpeg":
            rgba_image = image.convert("RGBA") if image.mode != "RGBA" else image.copy()
            background = Image.new("RGB", rgba_image.size, (255, 255, 255))
            background.paste(rgba_image, mask=rgba_image.getchannel("A"))
            return background
        if output_format == "gif":
            rgba_image = image.convert("RGBA") if image.mode != "RGBA" else image.copy()
            return rgba_image.convert("P", palette=Image.Palette.ADAPTIVE)
        if output_format == "png":
            if image.mode in {"RGBA", "RGB", "L"}:
                return image.copy()
            return image.convert("RGBA")
        if image.mode in {"RGBA", "RGB"}:
            return image.copy()
        return image.convert("RGBA")

    @staticmethod
    def _extension_for_output_format(output_format: str) -> str:
        return {
            "png": ".png",
            "gif": ".gif",
            "jpeg": ".jpg",
            "webp": ".webp",
            "svg": ".svg",
        }[output_format]
