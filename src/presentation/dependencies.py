"""Dependency container — lazy singleton wiring for use cases."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.application.batch_generate import BatchGenerateUseCase
from src.application.edit_figure import EditFigureUseCase
from src.application.evaluate_figure import EvaluateFigureUseCase
from src.application.generate_figure import GenerateFigureUseCase
from src.application.plan_figure import PlanFigureUseCase
from src.domain.exceptions import ConfigurationError
from src.infrastructure.config import load_config
from src.infrastructure.gemini_adapter import GeminiAdapter
from src.infrastructure.prompt_engine import PromptEngine
from src.infrastructure.pubmed_client import PubMedClient

if TYPE_CHECKING:
    from src.domain.interfaces import ImageGenerator


class Container:
    """Simple DI container — thread-unsafe singleton for MCP handlers."""

    _instance: Container | None = None

    def __init__(self) -> None:
        self._config = load_config()
        self._generator: ImageGenerator | None = None
        self._fetcher: PubMedClient | None = None
        self._prompt_builder: PromptEngine | None = None

    @classmethod
    def get(cls) -> Container:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def generator(self) -> ImageGenerator:
        if self._generator is None:
            if self._config.gemini.requires_api_key and not self._config.gemini.api_key:
                raise ConfigurationError(
                    f"{self._config.gemini.required_api_key_env} is not set. "
                    "Set it before starting the server with "
                    f"AFM_IMAGE_PROVIDER={self._config.gemini.provider}."
                )
            self._generator = GeminiAdapter(self._config.gemini)
        return self._generator

    @property
    def fetcher(self) -> PubMedClient:
        if self._fetcher is None:
            self._fetcher = PubMedClient()
        return self._fetcher

    @property
    def prompt_builder(self) -> PromptEngine:
        if self._prompt_builder is None:
            self._prompt_builder = PromptEngine()
        return self._prompt_builder

    @property
    def output_dir(self) -> str:
        return self._config.output_dir

    # ── Use case factories ──────────────────────────────────

    def generate_figure_uc(self) -> GenerateFigureUseCase:
        return GenerateFigureUseCase(
            fetcher=self.fetcher,
            generator=self.generator,
            prompt_builder=self.prompt_builder,
            provider_name=self._config.gemini.provider,
            output_dir=self.output_dir,
        )

    def plan_figure_uc(self) -> PlanFigureUseCase:
        return PlanFigureUseCase(
            fetcher=self.fetcher,
            prompt_builder=self.prompt_builder,
            provider_name=self._config.gemini.provider,
        )

    def edit_figure_uc(self) -> EditFigureUseCase:
        return EditFigureUseCase(generator=self.generator)

    def evaluate_figure_uc(self) -> EvaluateFigureUseCase:
        return EvaluateFigureUseCase(generator=self.generator)

    def batch_generate_uc(self) -> BatchGenerateUseCase:
        return BatchGenerateUseCase(generate_uc=self.generate_figure_uc())
