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

    from src.domain.entities import GenerationResult, Paper


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
    ) -> str: ...

    @abstractmethod
    def inject_journal_requirements(
        self,
        prompt: str,
        *,
        target_journal: str | None = None,
        source_journal: str | None = None,
    ) -> tuple[str, dict[str, object] | None]: ...
