from __future__ import annotations

from typing import TYPE_CHECKING

from src.infrastructure.config import OLLAMA_PROVIDER, OPENROUTER_PROVIDER, load_config

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


def test_load_config_exposes_cross_provider_fallback(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("AFM_IMAGE_PROVIDER", "google")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    config = load_config()

    assert config.gemini.fallback_provider == OPENROUTER_PROVIDER
