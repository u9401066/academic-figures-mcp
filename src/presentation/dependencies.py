"""Dependency container — lazy singleton wiring for use cases."""

from __future__ import annotations

from threading import Lock, RLock
from typing import TYPE_CHECKING, TypeVar, cast

from src.application.batch_generate import BatchGenerateUseCase
from src.application.composite_figure import CompositeFigureUseCase
from src.application.edit_figure import EditFigureUseCase
from src.application.evaluate_figure import EvaluateFigureUseCase
from src.application.generate_figure import GenerateFigureUseCase
from src.application.get_manifest_detail import GetManifestDetailUseCase
from src.application.list_manifests import ListManifestsUseCase
from src.application.multi_turn_edit import MultiTurnEditUseCase
from src.application.plan_figure import PlanFigureUseCase
from src.application.prepare_publication_image import PreparePublicationImageUseCase
from src.application.record_host_review import RecordHostReviewUseCase
from src.application.replay_manifest import ReplayManifestUseCase
from src.application.retarget_journal import RetargetJournalUseCase
from src.application.verify_figure import VerifyFigureUseCase
from src.domain.exceptions import ConfigurationError
from src.infrastructure.composite import CompositeFigureAssembler
from src.infrastructure.config import load_config
from src.infrastructure.file_metadata_fetcher import FileMetadataFetcher
from src.infrastructure.gemini_adapter import (
    GeminiAdapter,
    GeminiFigureEvaluator,
    GeminiImageVerifier,
)
from src.infrastructure.manifest_store import FileManifestStore
from src.infrastructure.output_formatter import PillowOutputFormatter
from src.infrastructure.prompt_engine import PromptEngine
from src.infrastructure.publication_image_processor import PillowPublicationImageProcessor
from src.infrastructure.pubmed_client import PubMedClient

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.application.multi_turn_edit import MultiTurnEditGenerator
    from src.domain.interfaces import (
        FigureComposer,
        FigureEvaluator,
        ImageGenerator,
        ImageVerifier,
        ManifestStore,
        MetadataFetcher,
        OutputFormatter,
        PromptBuilder,
        PublicationImageProcessor,
    )

T = TypeVar("T")


class Container:
    """Simple DI container with lock-protected singleton and lazy dependencies."""

    _instance: Container | None = None
    _instance_lock = Lock()

    def __init__(self) -> None:
        self._config = load_config()
        self._lazy_init_lock = RLock()
        self._generator: ImageGenerator | None = None
        self._fetcher: MetadataFetcher | None = None
        self._prompt_builder: PromptEngine | None = None
        self._manifest_store: FileManifestStore | None = None
        self._composer: CompositeFigureAssembler | None = None
        self._evaluator: FigureEvaluator | None = None
        self._verifier: ImageVerifier | None = None
        self._output_formatter: OutputFormatter | None = None
        self._publication_image_processor: PublicationImageProcessor | None = None

    @classmethod
    def get(cls) -> Container:
        instance = cls._instance
        if instance is not None:
            return instance

        with cls._instance_lock:
            instance = cls._instance
            if instance is None:
                instance = cls()
                cls._instance = instance
        return instance

    @classmethod
    def _reset_for_testing(cls) -> None:
        """Discard the singleton so the next `get()` creates a fresh container."""
        with cls._instance_lock:
            cls._instance = None

    def _get_or_create(self, attr_name: str, factory: Callable[[], T]) -> T:
        current = cast("T | None", getattr(self, attr_name))
        if current is not None:
            return current

        with self._lazy_init_lock:
            current = cast("T | None", getattr(self, attr_name))
            if current is None:
                current = factory()
                setattr(self, attr_name, current)
        return current

    def _build_generator(self) -> ImageGenerator:
        if self._config.gemini.requires_api_key and not self._config.gemini.api_key:
            raise ConfigurationError(
                f"{self._config.gemini.required_api_key_env} is not set. "
                "Set it before starting the server with "
                f"AFM_IMAGE_PROVIDER={self._config.gemini.provider}."
            )
        return GeminiAdapter(self._config.gemini)

    def _build_fetcher(self) -> MetadataFetcher:
        if self._config.metadata_source == "file":
            if not self._config.metadata_file:
                raise ConfigurationError(
                    "AFM_METADATA_FILE is required when AFM_METADATA_SOURCE=file."
                )
            return FileMetadataFetcher(self._config.metadata_file)
        return PubMedClient()

    def _build_prompt_builder(self) -> PromptBuilder:
        return PromptEngine()

    def _build_manifest_store(self) -> ManifestStore:
        return FileManifestStore(self._config.manifest_dir)

    def _build_composer(self) -> FigureComposer:
        return CompositeFigureAssembler()

    def _build_verifier(self) -> ImageVerifier:
        return GeminiImageVerifier(self._config.gemini)

    def _build_evaluator(self) -> FigureEvaluator:
        return GeminiFigureEvaluator(self._config.gemini)

    def _build_output_formatter(self) -> OutputFormatter:
        return PillowOutputFormatter()

    def _build_publication_image_processor(self) -> PublicationImageProcessor:
        return PillowPublicationImageProcessor()

    @property
    def generator(self) -> ImageGenerator:
        return self._get_or_create("_generator", self._build_generator)

    @property
    def fetcher(self) -> MetadataFetcher:
        return self._get_or_create("_fetcher", self._build_fetcher)

    @property
    def prompt_builder(self) -> PromptBuilder:
        return self._get_or_create("_prompt_builder", self._build_prompt_builder)

    @property
    def output_dir(self) -> str:
        return self._config.output_dir

    @property
    def manifest_store(self) -> ManifestStore:
        return self._get_or_create("_manifest_store", self._build_manifest_store)

    @property
    def composer(self) -> FigureComposer:
        return self._get_or_create("_composer", self._build_composer)

    @property
    def verifier(self) -> ImageVerifier:
        return self._get_or_create("_verifier", self._build_verifier)

    @property
    def evaluator(self) -> FigureEvaluator:
        return self._get_or_create("_evaluator", self._build_evaluator)

    @property
    def output_formatter(self) -> OutputFormatter:
        return self._get_or_create("_output_formatter", self._build_output_formatter)

    @property
    def publication_image_processor(self) -> PublicationImageProcessor:
        return self._get_or_create(
            "_publication_image_processor",
            self._build_publication_image_processor,
        )

    # ── Use case factories ──────────────────────────────────

    def generate_figure_uc(self) -> GenerateFigureUseCase:
        return GenerateFigureUseCase(
            fetcher=self.fetcher,
            generator=self.generator,
            prompt_builder=self.prompt_builder,
            planner=self.plan_figure_uc(),
            provider_name=self._config.gemini.provider,
            output_dir=self.output_dir,
            manifest_store=self.manifest_store,
            composer=self.composer,
            verifier=self.verifier,
            output_formatter=self.output_formatter,
        )

    def plan_figure_uc(self) -> PlanFigureUseCase:
        return PlanFigureUseCase(
            fetcher=self.fetcher,
            prompt_builder=self.prompt_builder,
            provider_name=self._config.gemini.provider,
        )

    def edit_figure_uc(self) -> EditFigureUseCase:
        return EditFigureUseCase(
            generator=self.generator,
            output_formatter=self.output_formatter,
        )

    def evaluate_figure_uc(self) -> EvaluateFigureUseCase:
        return EvaluateFigureUseCase(evaluator=self.evaluator)

    def batch_generate_uc(self) -> BatchGenerateUseCase:
        return BatchGenerateUseCase(generate_uc=self.generate_figure_uc())

    def composite_figure_uc(self) -> CompositeFigureUseCase:
        return CompositeFigureUseCase(composer=self.composer)

    def replay_manifest_uc(self) -> ReplayManifestUseCase:
        return ReplayManifestUseCase(
            manifest_store=self.manifest_store,
            generator=self.generator,
            verifier=self.verifier,
            default_output_dir=self.output_dir,
        )

    def record_host_review_uc(self) -> RecordHostReviewUseCase:
        return RecordHostReviewUseCase(manifest_store=self.manifest_store)

    def get_manifest_detail_uc(self) -> GetManifestDetailUseCase:
        return GetManifestDetailUseCase(manifest_store=self.manifest_store)

    def retarget_journal_uc(self) -> RetargetJournalUseCase:
        return RetargetJournalUseCase(
            manifest_store=self.manifest_store,
            generator=self.generator,
            prompt_builder=self.prompt_builder,
            verifier=self.verifier,
            default_output_dir=self.output_dir,
            provider_name=self._config.gemini.provider,
        )

    def list_manifests_uc(self) -> ListManifestsUseCase:
        return ListManifestsUseCase(manifest_store=self.manifest_store)

    def verify_figure_uc(self) -> VerifyFigureUseCase:
        return VerifyFigureUseCase(verifier=self.verifier)

    def multi_turn_edit_uc(self) -> MultiTurnEditUseCase:
        return MultiTurnEditUseCase(generator=cast("MultiTurnEditGenerator", self.generator))

    def prepare_publication_image_uc(self) -> PreparePublicationImageUseCase:
        return PreparePublicationImageUseCase(processor=self.publication_image_processor)
