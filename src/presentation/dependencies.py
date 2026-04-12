"""Dependency container — lazy singleton wiring for use cases."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.application.batch_generate import BatchGenerateUseCase
from src.application.edit_figure import EditFigureUseCase
from src.application.evaluate_figure import EvaluateFigureUseCase
from src.application.generate_figure import GenerateFigureUseCase
from src.application.list_manifests import ListManifestsUseCase
from src.application.plan_figure import PlanFigureUseCase
from src.application.poster import GeneratePosterUseCase, PlanPosterUseCase
from src.application.replay_manifest import ReplayManifestUseCase
from src.application.retarget_journal import RetargetJournalUseCase
from src.application.style import ApplyStyleUseCase, ExtractStyleUseCase, ListStylesUseCase
from src.domain.exceptions import ConfigurationError
from src.infrastructure.composite import CompositeFigureAssembler
from src.infrastructure.config import load_config
from src.infrastructure.gemini_adapter import GeminiAdapter
from src.infrastructure.manifest_store import FileManifestStore
from src.infrastructure.prompt_engine import PromptEngine
from src.infrastructure.pubmed_client import PubMedClient
from src.infrastructure.style_store import FileStyleStore

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
        self._manifest_store: FileManifestStore | None = None
        self._composer: CompositeFigureAssembler | None = None
        self._style_store: FileStyleStore | None = None

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

    @property
    def manifest_store(self) -> FileManifestStore:
        if self._manifest_store is None:
            self._manifest_store = FileManifestStore(self._config.manifest_dir)
        return self._manifest_store

    @property
    def composer(self) -> CompositeFigureAssembler:
        if self._composer is None:
            self._composer = CompositeFigureAssembler()
        return self._composer

    @property
    def style_store(self) -> FileStyleStore:
        if self._style_store is None:
            self._style_store = FileStyleStore()
        return self._style_store

    # ── Use case factories ──────────────────────────────────

    def generate_figure_uc(self) -> GenerateFigureUseCase:
        return GenerateFigureUseCase(
            fetcher=self.fetcher,
            generator=self.generator,
            prompt_builder=self.prompt_builder,
            provider_name=self._config.gemini.provider,
            output_dir=self.output_dir,
            manifest_store=self.manifest_store,
            composer=self.composer,
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

    def replay_manifest_uc(self) -> ReplayManifestUseCase:
        return ReplayManifestUseCase(
            manifest_store=self.manifest_store,
            generator=self.generator,
            default_output_dir=self.output_dir,
        )

    def retarget_journal_uc(self) -> RetargetJournalUseCase:
        return RetargetJournalUseCase(
            manifest_store=self.manifest_store,
            generator=self.generator,
            prompt_builder=self.prompt_builder,
            default_output_dir=self.output_dir,
            provider_name=self._config.gemini.provider,
        )

    def list_manifests_uc(self) -> ListManifestsUseCase:
        return ListManifestsUseCase(manifest_store=self.manifest_store)

    # ── Poster use cases (Theme 3) ──────────────────────────

    def plan_poster_uc(self) -> PlanPosterUseCase:
        return PlanPosterUseCase(
            fetcher=self.fetcher,
            prompt_builder=self.prompt_builder,
            provider_name=self._config.gemini.provider,
        )

    def generate_poster_uc(self) -> GeneratePosterUseCase:
        return GeneratePosterUseCase(
            fetcher=self.fetcher,
            generator=self.generator,
            prompt_builder=self.prompt_builder,
            provider_name=self._config.gemini.provider,
            output_dir=self.output_dir,
            manifest_store=self.manifest_store,
        )

    # ── Style use cases (Theme 4) ───────────────────────────

    def extract_style_uc(self) -> ExtractStyleUseCase:
        return ExtractStyleUseCase(
            generator=self.generator,
            style_store=self.style_store,
        )

    def apply_style_uc(self) -> ApplyStyleUseCase:
        return ApplyStyleUseCase(
            style_store=self.style_store,
            generator=self.generator,
            output_dir=self.output_dir,
        )

    def list_styles_uc(self) -> ListStylesUseCase:
        return ListStylesUseCase(style_store=self.style_store)
