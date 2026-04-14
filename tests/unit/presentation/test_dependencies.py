"""Container dependency wiring smoke tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from src.domain.exceptions import ConfigurationError
from src.infrastructure.config import STUB_PROVIDER, GeminiConfig, ServerConfig
from src.infrastructure.file_metadata_fetcher import FileMetadataFetcher
from src.infrastructure.stub_image_generator import StubImageGenerator, StubImageVerifier
from src.presentation.dependencies import Container

if TYPE_CHECKING:
    from pathlib import Path


class TestContainerReset:
    """Verify _reset_for_testing clears the singleton."""

    def teardown_method(self) -> None:
        Container._reset_for_testing()

    @patch("src.presentation.dependencies.load_config")
    def test_reset_creates_fresh_instance(self, mock_cfg: object) -> None:
        first = Container.get()
        Container._reset_for_testing()
        second = Container.get()
        assert first is not second

    @patch("src.presentation.dependencies.load_config")
    def test_get_returns_same_instance(self, mock_cfg: object) -> None:
        a = Container.get()
        b = Container.get()
        assert a is b

    @patch("src.presentation.dependencies.load_config")
    def test_fetcher_uses_file_metadata_source(self, mock_cfg: object, tmp_path: Path) -> None:
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
    def test_fetcher_requires_metadata_file_for_file_source(self, mock_cfg: object) -> None:
        mock_cfg.return_value = ServerConfig(metadata_source="file", metadata_file=None)

        with pytest.raises(ConfigurationError, match="AFM_METADATA_FILE"):
            _ = Container.get().fetcher

    @patch("src.presentation.dependencies.load_config")
    def test_stub_provider_uses_offline_paths(self, mock_cfg: object) -> None:
        mock_cfg.return_value = ServerConfig(gemini=GeminiConfig(provider=STUB_PROVIDER))

        container = Container.get()

        assert isinstance(container.generator, StubImageGenerator)
        assert isinstance(container.verifier, StubImageVerifier)
