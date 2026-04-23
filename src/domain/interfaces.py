"""Abstract interfaces — domain defines WHAT, infrastructure implements HOW.

Rules:
  - Only stdlib imports allowed in this file.
  - Infrastructure modules implement these ABCs.
  - Application layer depends on these interfaces, never on concrete classes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path

    from src.domain.entities import GenerationManifest, GenerationResult, Paper
    from src.domain.value_objects import QualityVerdict


class MetadataFetcher(Protocol):
    """Fetches paper metadata from an external catalog."""

    def fetch_paper(self, pmid: str) -> Paper: ...


class ImageGenerator(Protocol):
    """Generates or edits images from prompts."""

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        aspect_ratio: str | None = None,
    ) -> GenerationResult: ...

    def edit(
        self,
        image_path: Path,
        instruction: str,
        *,
        model: str | None = None,
    ) -> GenerationResult: ...


class OutputFormatter(Protocol):
    """Normalizes requested output formats and converts generated assets."""

    def normalize_output_format(self, value: str | None) -> str | None: ...

    def media_type_for_output_format(self, output_format: str) -> str: ...

    def convert_generation_result(
        self,
        result: GenerationResult,
        output_format: str | None,
    ) -> GenerationResult: ...

    def convert_file(self, path: Path, output_format: str | None) -> Path: ...


class PublicationImageProcessor(Protocol):
    """Prepares raster image files for publication delivery constraints."""

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
    ) -> dict[str, object]: ...


class PromptBuilder(Protocol):
    """Builds structured prompts for image generation."""

    def build_prompt(
        self,
        paper: Paper,
        figure_type: str,
        language: str,
        output_size: str,
        expected_labels: list[str] | None = None,
    ) -> str: ...

    def inject_journal_requirements(
        self,
        prompt: str,
        *,
        target_journal: str | None = None,
        source_journal: str | None = None,
    ) -> tuple[str, dict[str, object] | None]: ...


class ManifestStore(Protocol):
    """Persists generation manifests for replay and audit."""

    def save(self, manifest: GenerationManifest) -> GenerationManifest: ...

    def load(self, manifest_id: str) -> GenerationManifest: ...

    def list(self, limit: int = 20) -> list[GenerationManifest]: ...


class FigureComposer(Protocol):
    """Assembles multi-panel figures into a single output."""

    def compose(
        self,
        panels: list[dict[str, str]],
        *,
        title: str,
        caption: str,
        citation: str,
        output_path: str | None = None,
    ) -> dict[str, object]: ...


class FigureEvaluator(Protocol):
    """Evaluates an existing figure and returns textual review output."""

    def evaluate(
        self,
        image_path: Path,
        instruction: str,
        *,
        model: str | None = None,
    ) -> GenerationResult: ...


class ImageVerifier(Protocol):
    """Verifies generated figure quality via vision / self-check."""

    def verify(
        self,
        image_bytes: bytes,
        *,
        expected_labels: list[str],
        figure_type: str,
        language: str,
    ) -> QualityVerdict: ...
