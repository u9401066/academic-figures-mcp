from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.domain.exceptions import ConfigurationError
from src.infrastructure.config import (
    METADATA_SOURCE_FILE,
    OLLAMA_PROVIDER,
    OPENAI_PROVIDER,
    OPENROUTER_PROVIDER,
    load_config,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_load_config_accepts_ollama_provider(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AFM_IMAGE_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OLLAMA_MODEL", "llava:34b")

    config = load_config()

    assert config.gemini.provider == OLLAMA_PROVIDER
    assert config.gemini.is_ollama is True
    assert config.gemini.requires_api_key is False
    assert config.gemini.default_model == "llava:34b"
    assert config.gemini.ollama_base_url == "http://localhost:11434/v1"


def test_load_config_accepts_openai_provider(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AFM_IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    monkeypatch.setenv("OPENAI_IMAGE_SIZE", "1024x1536")

    config = load_config()

    assert config.gemini.provider == OPENAI_PROVIDER
    assert config.gemini.is_openai is True
    assert config.gemini.requires_api_key is True
    assert config.gemini.required_api_key_env == "OPENAI_API_KEY"
    assert config.gemini.default_model == "gpt-image-2"
    assert config.gemini.openai_image_size == "1024x1536"


def test_load_config_rejects_unknown_provider(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AFM_IMAGE_PROVIDER", "typo-provider")

    with pytest.raises(ConfigurationError, match="Unsupported AFM_IMAGE_PROVIDER"):
        load_config()


def test_load_config_exposes_cross_provider_fallback(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AFM_IMAGE_PROVIDER", "google")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    config = load_config()

    assert config.gemini.fallback_provider == OPENROUTER_PROVIDER


def test_load_config_accepts_file_metadata_source(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AFM_METADATA_SOURCE", "file")
    monkeypatch.setenv("AFM_METADATA_FILE", "/tmp/papers.yaml")

    config = load_config()

    assert config.metadata_source == METADATA_SOURCE_FILE
    assert config.metadata_file == "/tmp/papers.yaml"
