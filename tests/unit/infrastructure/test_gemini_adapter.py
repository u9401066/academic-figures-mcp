from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.entities import GenerationResult
from src.infrastructure.config import GOOGLE_PROVIDER, OLLAMA_PROVIDER, GeminiConfig
from src.infrastructure.gemini_adapter import GeminiAdapter

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


def test_google_generate_falls_back_to_alternate_provider(monkeypatch: MonkeyPatch) -> None:
    config = GeminiConfig(
        provider=GOOGLE_PROVIDER,
        google_api_key="google-key",
        openrouter_api_key="openrouter-key",
        max_attempts=1,
        retry_backoff_seconds=0.0,
        enable_provider_fallback=True,
    )
    adapter = GeminiAdapter(config)

    class StubFallbackAdapter:
        def generate(
            self,
            prompt: str,
            *,
            aspect_ratio: str | None = None,
            model: str | None = None,
        ) -> GenerationResult:
            return GenerationResult(image_bytes=b"fallback-image", model="fallback-model")

    monkeypatch.setattr(
        adapter,
        "_call_with_retry",
        lambda operation: (None, "429 quota exceeded"),
    )
    monkeypatch.setattr(
        adapter,
        "_fallback_adapter",
        lambda error: StubFallbackAdapter(),
    )

    result = adapter.generate("academic figure prompt")

    assert result.ok is True
    assert result.model == "fallback-model"


def test_ollama_generate_returns_svg(monkeypatch: MonkeyPatch) -> None:
    config = GeminiConfig(
        provider=OLLAMA_PROVIDER,
        default_model="llava:latest",
        ollama_model="llava:latest",
        enable_provider_fallback=False,
    )
    adapter = GeminiAdapter(config)
    ollama_response = (
        '{"title":"Sepsis Workflow","subtitle":"Local plan",'
        '"sections":[{"heading":"Recognition","bullets":["Identify shock"]}],'
        '"footer":"PMID 123","accent_color":"#004488"}'
    )

    monkeypatch.setattr(
        adapter,
        "_ollama_chat",
        lambda **kwargs: (ollama_response, None),
    )

    result = adapter.generate("## Block 7: SIZE\ncanvas: 800x1200")

    assert result.ok is True
    assert result.media_type == "image/svg+xml"
    assert result.file_extension == ".svg"
    assert result.image_bytes is not None
    assert b"<svg" in result.image_bytes


def test_ollama_edit_supports_evaluation_text(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config = GeminiConfig(
        provider=OLLAMA_PROVIDER,
        default_model="llava:latest",
        ollama_model="llava:latest",
        enable_provider_fallback=False,
    )
    adapter = GeminiAdapter(config)
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"fake-png")

    monkeypatch.setattr(adapter, "_ollama_chat", lambda **kwargs: ("overall score: 4/5", None))

    result = adapter.edit(
        image_path,
        "Evaluate this academic figure and give an overall score",
    )

    assert result.text == "overall score: 4/5"
    assert result.error == ""
