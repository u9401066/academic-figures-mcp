"""Pillow-backed raster preparation for publication DPI constraints."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from PIL import Image, UnidentifiedImageError

from src.domain.exceptions import ValidationError
from src.domain.interfaces import PublicationImageProcessor

_MM_PER_INCH = 25.4

if TYPE_CHECKING:
    from pathlib import Path


class PillowPublicationImageProcessor(PublicationImageProcessor):
    """Resize and write DPI metadata without invoking any generative provider."""

    _FORMAT_TO_EXTENSION: ClassVar[dict[str, str]] = {
        "png": ".png",
        "jpeg": ".jpg",
        "tiff": ".tif",
    }
    _FORMAT_TO_PIL_FORMAT: ClassVar[dict[str, str]] = {
        "png": "PNG",
        "jpeg": "JPEG",
        "tiff": "TIFF",
    }
    _EXTENSION_TO_FORMAT: ClassVar[dict[str, str]] = {
        ".png": "png",
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".tif": "tiff",
        ".tiff": "tiff",
    }

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
        normalized_format = self._resolve_output_format(
            output_format=output_format,
            output_path=output_path,
            image_path=image_path,
        )
        final_output_path = self._resolve_output_path(
            image_path=image_path,
            output_path=output_path,
            output_format=normalized_format,
        )

        try:
            with Image.open(image_path) as image:
                source = image.copy()
                original_size = source.size
                original_dpi = self._read_dpi(image)
        except UnidentifiedImageError as exc:
            raise ValidationError("image_path must point to a readable raster image") from exc

        target_size = self._target_pixel_size(
            original_size=original_size,
            target_dpi=target_dpi,
            width_mm=width_mm,
            height_mm=height_mm,
            preserve_aspect_ratio=preserve_aspect_ratio,
        )
        upscaled = target_size[0] > original_size[0] or target_size[1] > original_size[1]
        if upscaled and not allow_upscale:
            raise ValidationError(
                "Requested print size requires upscaling; set allow_upscale=true "
                "or provide a smaller width_mm/height_mm."
            )

        warnings: list[str] = []
        if upscaled:
            warnings.append(
                "Image was upscaled with Lanczos resampling; this meets pixel dimensions "
                "but cannot add new scientific detail."
            )
        if width_mm is None and height_mm is None:
            warnings.append(
                "No final print size was provided; preserved pixel dimensions and wrote "
                "600 DPI metadata only."
            )

        prepared = source
        if target_size != original_size:
            prepared = source.resize(target_size, Image.Resampling.LANCZOS)
        prepared = self._prepare_for_output_format(prepared, output_format=normalized_format)

        final_output_path.parent.mkdir(parents=True, exist_ok=True)
        save_kwargs: dict[str, object] = {"dpi": (target_dpi, target_dpi)}
        if normalized_format == "jpeg":
            save_kwargs["quality"] = 95
            save_kwargs["subsampling"] = 0
        prepared.save(
            final_output_path,
            format=self._FORMAT_TO_PIL_FORMAT[normalized_format],
            **save_kwargs,
        )

        output_width_mm = self._px_to_mm(target_size[0], target_dpi)
        output_height_mm = self._px_to_mm(target_size[1], target_dpi)
        scale_factor = max(
            target_size[0] / original_size[0],
            target_size[1] / original_size[1],
        )
        return {
            "output_path": str(final_output_path),
            "output_format": normalized_format,
            "original_width_px": original_size[0],
            "original_height_px": original_size[1],
            "output_width_px": target_size[0],
            "output_height_px": target_size[1],
            "original_dpi": original_dpi,
            "output_dpi": target_dpi,
            "output_width_mm": round(output_width_mm, 2),
            "output_height_mm": round(output_height_mm, 2),
            "resampled": target_size != original_size,
            "upscaled": upscaled,
            "scale_factor": round(scale_factor, 4),
            "image_size_bytes": final_output_path.stat().st_size,
            "warnings": warnings,
        }

    @classmethod
    def normalize_output_format(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized == "jpg":
            return "jpeg"
        if normalized in {"tif", "tiff"}:
            return "tiff"
        if normalized not in cls._FORMAT_TO_EXTENSION:
            supported = ", ".join(sorted(cls._FORMAT_TO_EXTENSION))
            raise ValidationError(f"publication output_format must be one of: {supported}")
        return normalized

    @classmethod
    def _resolve_output_format(
        cls,
        *,
        output_format: str | None,
        output_path: Path | None,
        image_path: Path,
    ) -> str:
        normalized = cls.normalize_output_format(output_format)
        if normalized is not None:
            return normalized

        for path in (output_path, image_path):
            if path is None:
                continue
            from_suffix = cls._EXTENSION_TO_FORMAT.get(path.suffix.lower())
            if from_suffix is not None:
                return from_suffix
        return "png"

    @classmethod
    def _resolve_output_path(
        cls,
        *,
        image_path: Path,
        output_path: Path | None,
        output_format: str,
    ) -> Path:
        extension = cls._FORMAT_TO_EXTENSION[output_format]
        if output_path is None:
            return image_path.with_name(f"{image_path.stem}_600dpi{extension}")
        if output_path.suffix:
            return output_path
        return output_path.with_suffix(extension)

    @classmethod
    def _target_pixel_size(
        cls,
        *,
        original_size: tuple[int, int],
        target_dpi: int,
        width_mm: float | None,
        height_mm: float | None,
        preserve_aspect_ratio: bool,
    ) -> tuple[int, int]:
        original_width, original_height = original_size
        if width_mm is None and height_mm is None:
            return original_size

        target_width = cls._mm_to_px(width_mm, target_dpi) if width_mm is not None else 0
        target_height = cls._mm_to_px(height_mm, target_dpi) if height_mm is not None else 0

        if width_mm is not None and height_mm is None:
            target_height = max(1, round(target_width * original_height / original_width))
        elif height_mm is not None and width_mm is None:
            target_width = max(1, round(target_height * original_width / original_height))
        elif preserve_aspect_ratio:
            scale = min(target_width / original_width, target_height / original_height)
            target_width = max(1, round(original_width * scale))
            target_height = max(1, round(original_height * scale))

        return (max(1, target_width), max(1, target_height))

    @staticmethod
    def _mm_to_px(value_mm: float, dpi: int) -> int:
        return max(1, round(value_mm / _MM_PER_INCH * dpi))

    @staticmethod
    def _px_to_mm(value_px: int, dpi: int) -> float:
        return value_px / dpi * _MM_PER_INCH

    @staticmethod
    def _read_dpi(image: Image.Image) -> tuple[float, float] | None:
        dpi = image.info.get("dpi")
        if not isinstance(dpi, tuple) or len(dpi) < 2:
            return None
        x_dpi, y_dpi = dpi[0], dpi[1]
        if not isinstance(x_dpi, (int, float)) or not isinstance(y_dpi, (int, float)):
            return None
        return (round(float(x_dpi), 2), round(float(y_dpi), 2))

    @staticmethod
    def _prepare_for_output_format(image: Image.Image, *, output_format: str) -> Image.Image:
        if output_format == "jpeg":
            rgba_image = image.convert("RGBA") if image.mode != "RGBA" else image
            background = Image.new("RGB", rgba_image.size, (255, 255, 255))
            background.paste(rgba_image, mask=rgba_image.getchannel("A"))
            return background
        if image.mode in {"RGB", "RGBA", "L"}:
            return image
        return image.convert("RGBA")
