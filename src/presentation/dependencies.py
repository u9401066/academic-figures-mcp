"""Dependency container — lazy singleton wiring for use cases."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.application.batch_generate import BatchGenerateUseCase
from src.application.composite_figure import CompositeFigureUseCase
from src.application.edit_figure import EditFigureUseCase
from src.application.evaluate_figure import EvaluateFigureUseCase
from src.application.generate_figure import GenerateFigureUseCase
from src.application.list_manifests import ListManifestsUseCase
from src.application.multi_turn_edit import MultiTurnEditUseCase
from src.application.plan_figure import PlanFigureUseCase
from src.application.replay_manifest import ReplayManifestUseCase
from src.application.retarget_journal import RetargetJournalUseCase
from src.application.verify_figure import VerifyFigureUseCase
from src.domain.exceptions import ConfigurationError
from src.infrastructure.composite import CompositeFigureAssembler
from src.infrastructure.config import load_config
from src.infrastructure.file_metadata_fetcher import FileMetadataFetcher
from src.infrastructure.gemini_adapter import GeminiAdapter, GeminiImageVerifier
from src.infrastructure.manifest_store import FileManifestStore
from src.infrastructure.prompt_engine import PromptEngine
from src.infrastructure.pubmed_client import PubMedClient

if TYPE_CHECKING:
    from src.domain.interfaces import (
        FigureComposer,
        ImageGenerator,
        ImageVerifier,
        ManifestStore,
        MetadataFetcher,
        PromptBuilder,
    )


class Container:
    """Simple DI container — thread-unsafe singleton for MCP handlers."""

    _instance: Container | None = None

    def __init__(self) -> None:
        self._config = load_config()
        self._generator: ImageGenerator | None = None
        self._fetcher: MetadataFetcher | None = None
        self._prompt_builder: PromptEngine | None = None
        self._manifest_store: FileManifestStore | None = None
        self._composer: CompositeFigureAssembler | None = None
        self._verifier: ImageVerifier | None = None

    @classmethod
    def get(cls) -> Container:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def _reset_for_testing(cls) -> None:
        """Discard the singleton so the next `get()` creates a fresh container."""
        cls._instance = None

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
    def fetcher(self) -> MetadataFetcher:
        if self._fetcher is None:
            if self._config.metadata_source == "file":
                if not self._config.metadata_file:
                    raise ConfigurationError(
                        "AFM_METADATA_FILE is required when AFM_METADATA_SOURCE=file."
                    )
                self._fetcher = FileMetadataFetcher(self._config.metadata_file)
            else:
                self._fetcher = PubMedClient()
        return self._fetcher

    @property
    def prompt_builder(self) -> PromptBuilder:
        if self._prompt_builder is None:
            self._prompt_builder = PromptEngine()
        return self._prompt_builder

    @property
    def output_dir(self) -> str:
        return self._config.output_dir

    @property
    def manifest_store(self) -> ManifestStore:
        if self._manifest_store is None:
            self._manifest_store = FileManifestStore(self._config.manifest_dir)
        return self._manifest_store

    @property
    def composer(self) -> FigureComposer:
        if self._composer is None:
            self._composer = CompositeFigureAssembler()
        return self._composer

    @property
    def verifier(self) -> ImageVerifier:
        if self._verifier is None:
            self._verifier = GeminiImageVerifier(self._config.gemini)
        return self._verifier

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
            verifier=self.verifier,
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

    def composite_figure_uc(self) -> CompositeFigureUseCase:
        return CompositeFigureUseCase(composer=self.composer)

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

    def verify_figure_uc(self) -> VerifyFigureUseCase:
        return VerifyFigureUseCase(verifier=self.verifier)

    def multi_turn_edit_uc(self) -> MultiTurnEditUseCase:
        return MultiTurnEditUseCase(generator=self.generator)
