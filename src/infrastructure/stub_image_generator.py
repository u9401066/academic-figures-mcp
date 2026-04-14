"""Offline stub image generator and verifier for CI/package smoke."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Final

from src.domain.entities import GenerationResult
from src.domain.interfaces import ImageGenerator, ImageVerifier
from src.domain.value_objects import EVAL_DOMAINS, QualityVerdict

if TYPE_CHECKING:
    from pathlib import Path
_STUB_PNG_BYTES: Final[bytes] = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAukB9p6U4tQAAAAASUVORK5CYII="
)


def _guess_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".gif":
        return "image/gif"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".svg":
        return "image/svg+xml"
    return "image/png"


class StubImageGenerator(ImageGenerator):
    """Deterministic, offline-safe generator for CI and smoke tests."""

    def __init__(self) -> None:
        self.last_prompt = ""

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        aspect_ratio: str | None = None,
    ) -> GenerationResult:
        del model, aspect_ratio
        self.last_prompt = prompt
        return GenerationResult(
            image_bytes=_STUB_PNG_BYTES,
            text="stub image generated",
            model="stub-generator",
            elapsed_seconds=0.01,
            media_type="image/png",
        )

    def edit(
        self,
        image_path: Path,
        instruction: str,
        *,
        model: str | None = None,
    ) -> GenerationResult:
        del instruction, model
        media_type = _guess_media_type(image_path)
        data = image_path.read_bytes() if image_path.exists() else _STUB_PNG_BYTES
        return GenerationResult(
            image_bytes=data,
            text="stub edit applied",
            model="stub-generator",
            elapsed_seconds=0.01,
            media_type=media_type,
        )


class StubImageVerifier(ImageVerifier):
    """Offline verifier that always passes with deterministic scores."""

    def verify(
        self,
        image_bytes: bytes,
        *,
        expected_labels: list[str],
        figure_type: str,
        language: str,
    ) -> QualityVerdict:
        del image_bytes, figure_type, language
        domain_scores = {domain: 5.0 for domain in EVAL_DOMAINS}
        text_passed = True if expected_labels else None
        return QualityVerdict(
            passed=True,
            domain_scores=domain_scores,
            total_score=sum(domain_scores.values()),
            critical_issues=(),
            text_verification_passed=text_passed,
            missing_labels=(),
            summary="Stub verification passed (offline mode)",
        )
