"""Abstract interfaces — domain defines WHAT, infrastructure implements HOW.

Rules:
  - Only stdlib imports allowed in this file.
  - Infrastructure modules implement these ABCs.
  - Application layer depends on these interfaces, never on concrete classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from src.domain.entities import GenerationManifest, GenerationResult, Paper
    from src.domain.value_objects import QualityVerdict


class MetadataFetcher(ABC):
    """Fetches paper metadata from an external catalog."""

    @abstractmethod
    def fetch_paper(self, pmid: str) -> Paper: ...


class ImageGenerator(ABC):
    """Generates or edits images from prompts."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        aspect_ratio: str | None = None,
    ) -> GenerationResult: ...

    @abstractmethod
    def edit(
        self,
        image_path: Path,
        instruction: str,
        *,
        model: str | None = None,
    ) -> GenerationResult: ...


class PromptBuilder(ABC):
    """Builds structured prompts for image generation."""

    @abstractmethod
    def build_prompt(
        self,
        paper: Paper,
        figure_type: str,
        language: str,
        output_size: str,
        expected_labels: list[str] | None = None,
    ) -> str: ...

    @abstractmethod
    def inject_journal_requirements(
        self,
        prompt: str,
        *,
        target_journal: str | None = None,
        source_journal: str | None = None,
    ) -> tuple[str, dict[str, object] | None]: ...


class ManifestStore(ABC):
    """Persists generation manifests for replay and audit."""

    @abstractmethod
    def save(self, manifest: GenerationManifest) -> GenerationManifest: ...

    @abstractmethod
    def load(self, manifest_id: str) -> GenerationManifest: ...

    @abstractmethod
    def list(self, limit: int = 20) -> list[GenerationManifest]: ...


class FigureComposer(ABC):
    """Assembles multi-panel figures into a single output."""

    @abstractmethod
    def compose(
        self,
        panels: list[dict[str, str]],
        *,
        title: str,
        caption: str,
        citation: str,
        output_path: str | None = None,
    ) -> dict[str, object]: ...


class ImageVerifier(ABC):
    """Verifies generated figure quality via vision / self-check."""

    @abstractmethod
    def verify(
        self,
        image_bytes: bytes,
        *,
        expected_labels: list[str],
        figure_type: str,
        language: str,
    ) -> QualityVerdict: ...
