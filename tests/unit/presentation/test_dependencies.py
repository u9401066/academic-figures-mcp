"""Container dependency wiring smoke tests."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from src.domain.exceptions import ConfigurationError
from src.infrastructure.config import OLLAMA_PROVIDER, GeminiConfig, ServerConfig
from src.infrastructure.file_metadata_fetcher import FileMetadataFetcher
from src.presentation.dependencies import Container

if TYPE_CHECKING:
    from pathlib import Path


class TestContainerReset:
    """Verify _reset_for_testing clears the singleton."""

    def teardown_method(self) -> None:
        Container._reset_for_testing()

    @patch("src.presentation.dependencies.load_config")
    def test_reset_creates_fresh_instance(self, mock_cfg: MagicMock) -> None:
        first = Container.get()
        Container._reset_for_testing()
        second = Container.get()
        assert first is not second

    @patch("src.presentation.dependencies.load_config")
    def test_get_returns_same_instance(self, mock_cfg: MagicMock) -> None:
        a = Container.get()
        b = Container.get()
        assert a is b

    @patch("src.presentation.dependencies.load_config")
    def test_fetcher_uses_file_metadata_source(
        self,
        mock_cfg: MagicMock,
        tmp_path: Path,
    ) -> None:
        data_file = tmp_path / "papers.yaml"
        data_file.write_text(
            "papers:\n  - pmid: '12345678'\n    title: File-backed paper\n",
            encoding="utf-8",
        )
        mock_cfg.return_value = ServerConfig(metadata_source="file", metadata_file=str(data_file))

        fetcher = Container.get().fetcher

        assert isinstance(fetcher, FileMetadataFetcher)
        assert fetcher.fetch_paper("12345678").title == "File-backed paper"

    @patch("src.presentation.dependencies.load_config")
    def test_fetcher_requires_metadata_file_for_file_source(
        self,
        mock_cfg: MagicMock,
    ) -> None:
        mock_cfg.return_value = ServerConfig(metadata_source="file", metadata_file=None)

        with pytest.raises(ConfigurationError, match="AFM_METADATA_FILE"):
            _ = Container.get().fetcher

    @patch("src.presentation.dependencies.load_config")
    def test_get_initializes_singleton_once_under_concurrency(
        self,
        mock_cfg: MagicMock,
    ) -> None:
        def delayed_config() -> ServerConfig:
            time.sleep(0.02)
            return ServerConfig(gemini=GeminiConfig(provider=OLLAMA_PROVIDER))

        mock_cfg.side_effect = delayed_config
        barrier = threading.Barrier(6)
        instances: list[Container] = []
        errors: list[Exception] = []

        def worker() -> None:
            try:
                barrier.wait()
                instances.append(Container.get())
            except Exception as exc:  # pragma: no cover - test failure capture
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors
        assert len(instances) == 6
        assert mock_cfg.call_count == 1
        assert len({id(instance) for instance in instances}) == 1

    @patch("src.presentation.dependencies.GeminiAdapter")
    @patch("src.presentation.dependencies.load_config")
    def test_generator_initializes_once_under_concurrency(
        self,
        mock_cfg: MagicMock,
        mock_adapter_cls: MagicMock,
    ) -> None:
        mock_cfg.return_value = ServerConfig(gemini=GeminiConfig(provider=OLLAMA_PROVIDER))

        class StubAdapter:
            def __init__(self, config: GeminiConfig) -> None:
                time.sleep(0.02)
                self.config = config

        mock_adapter_cls.side_effect = StubAdapter
        container = Container.get()
        barrier = threading.Barrier(6)
        generators: list[object] = []
        errors: list[Exception] = []

        def worker() -> None:
            try:
                barrier.wait()
                generators.append(container.generator)
            except Exception as exc:  # pragma: no cover - test failure capture
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors
        assert len(generators) == 6
        assert mock_adapter_cls.call_count == 1
        assert len({id(generator) for generator in generators}) == 1
