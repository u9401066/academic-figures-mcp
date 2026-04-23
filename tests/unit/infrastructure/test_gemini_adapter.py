from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.entities import GenerationResult
from src.domain.value_objects import EVAL_DOMAINS
from src.infrastructure.config import GOOGLE_PROVIDER, OLLAMA_PROVIDER, GeminiConfig
from src.infrastructure.gemini_adapter import (
    GeminiAdapter,
    GeminiFigureEvaluator,
    GeminiImageVerifier,
    _detect_image_media_type,
)
from src.infrastructure.gemini_provider_runtimes import (
    ProviderFailure,
    ProviderFailureKind,
    RuntimeOutcome,
    parse_openrouter_image_response,
)

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
        adapter._generation,
        "_call_with_retry",
        lambda operation: (
            None,
            ProviderFailure(
                kind=ProviderFailureKind.TRANSIENT,
                message="429 quota exceeded",
            ),
        ),
    )
    monkeypatch.setattr(
        adapter._generation._fallback_router,
        "maybe_generate",
        lambda **kwargs: StubFallbackAdapter().generate(kwargs["prompt"]),
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
        adapter._generation._runtime,
        "generate",
        lambda **kwargs: RuntimeOutcome.success(
            GenerationResult(
                image_bytes=b"<svg></svg>",
                text=ollama_response,
                model=kwargs["model_name"],
                media_type="image/svg+xml",
            )
        ),
    )

    result = adapter.generate("## Block 7: SIZE\ncanvas: 800x1200")

    assert result.ok is True
    assert result.media_type == "image/svg+xml"
    assert result.file_extension == ".svg"
    assert result.image_bytes is not None
    assert b"<svg" in result.image_bytes


def test_ollama_figure_evaluator_returns_evaluation_text(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    config = GeminiConfig(
        provider=OLLAMA_PROVIDER,
        default_model="llava:latest",
        ollama_model="llava:latest",
        enable_provider_fallback=False,
    )
    evaluator = GeminiFigureEvaluator(config)
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"fake-png")

    monkeypatch.setattr(
        evaluator._runtime,
        "evaluate",
        lambda **kwargs: RuntimeOutcome.success(
            GenerationResult(text="overall score: 4/5", model=kwargs["model_name"])
        ),
    )

    result = evaluator.evaluate(
        image_path,
        "Evaluate this academic figure and give an overall score",
    )

    assert result.text == "overall score: 4/5"
    assert result.error == ""


def test_ollama_image_verifier_uses_runtime_evaluate(monkeypatch: MonkeyPatch) -> None:
    config = GeminiConfig(
        provider=OLLAMA_PROVIDER,
        default_model="llava:latest",
        ollama_model="llava:latest",
        enable_provider_fallback=False,
    )
    verifier = GeminiImageVerifier(config)
    verification_text = "\n".join(f"{domain}: 4 solid" for domain in EVAL_DOMAINS)

    monkeypatch.setattr(
        verifier._runtime,
        "evaluate",
        lambda **kwargs: RuntimeOutcome.success(
            GenerationResult(text=verification_text, model=kwargs["model_name"])
        ),
    )

    verdict = verifier.verify(
        b"fake-png",
        expected_labels=[],
        figure_type="infographic",
        language="en",
    )

    assert verdict.passed is True
    assert verdict.total_score == float(len(EVAL_DOMAINS) * 4)
    assert verdict.summary == verification_text


def test_image_verifier_parse_passing_verdict() -> None:
    text = (
        "text_accuracy: 5 Excellent\n"
        "anatomy: 4 Good\n"
        "color: 5 Perfect\n"
        "layout: 4 Nice\n"
        "scientific_accuracy: 4 Correct\n"
        "legibility: 5 Clear\n"
        "visual_polish: 4 Polished\n"
        "citation: 5 Present\n"
    )

    verdict = GeminiImageVerifier._parse_verdict(text, expected_labels=[])

    assert verdict.passed is True
    assert verdict.total_score == 36.0
    assert verdict.domain_scores["text_accuracy"] == 5.0


def test_image_verifier_parse_failing_verdict() -> None:
    text = (
        "text_accuracy: 2 Poor\n"
        "anatomy: 2 Inaccurate\n"
        "color: 2 Bad\n"
        "layout: 2 Messy\n"
        "scientific_accuracy: 2 Wrong\n"
        "legibility: 2 Unreadable\n"
        "visual_polish: 2 Rough\n"
        "citation: 2 Missing\n"
        "CRITICAL: All text is garbled."
    )

    verdict = GeminiImageVerifier._parse_verdict(text, expected_labels=[])

    assert verdict.passed is False
    assert len(verdict.critical_issues) > 0


def test_image_verifier_parse_missing_labels() -> None:
    text = (
        "text_accuracy: 4 OK\n"
        "anatomy: 4 OK\n"
        "color: 4 OK\n"
        "layout: 4 OK\n"
        "scientific_accuracy: 4 OK\n"
        "legibility: 4 OK\n"
        "visual_polish: 4 OK\n"
        "citation: 4 OK\n"
        "Label check:\n"
        "急性冠心症: FOUND_EXACT\n"
        "處置流程: MISSING in the figure\n"
    )

    verdict = GeminiImageVerifier._parse_verdict(
        text, expected_labels=["急性冠心症", "處置流程"]
    )

    assert verdict.text_verification_passed is False
    assert "處置流程" in verdict.missing_labels


def test_image_verifier_passes_when_all_labels_found() -> None:
    text = (
        "text_accuracy: 4 OK\n"
        "anatomy: 4 OK\n"
        "color: 4 OK\n"
        "layout: 4 OK\n"
        "scientific_accuracy: 4 OK\n"
        "legibility: 4 OK\n"
        "visual_polish: 4 OK\n"
        "citation: 4 OK\n"
        "All labels found correctly."
    )

    verdict = GeminiImageVerifier._parse_verdict(
        text, expected_labels=["急性冠心症", "處置流程"]
    )

    assert verdict.text_verification_passed is True
    assert len(verdict.missing_labels) == 0


def test_image_verifier_surfaces_typed_runtime_failure(monkeypatch: MonkeyPatch) -> None:
    config = GeminiConfig(
        provider=GOOGLE_PROVIDER,
        google_api_key="google-key",
        enable_provider_fallback=False,
    )
    verifier = GeminiImageVerifier(config)

    monkeypatch.setattr(
        verifier._runtime,
        "evaluate",
        lambda **kwargs: RuntimeOutcome.failed(
            ProviderFailure(
                kind=ProviderFailureKind.PERMANENT,
                message="provider unavailable",
            )
        ),
    )

    verdict = verifier.verify(
        b"fake-png",
        expected_labels=[],
        figure_type="infographic",
        language="en",
    )

    assert verdict.passed is False
    assert verdict.summary.startswith("Vision verification failed: provider unavailable")


def test_ollama_edit_rejects_bitmap_image_editing(tmp_path: Path) -> None:
    config = GeminiConfig(
        provider=OLLAMA_PROVIDER,
        default_model="llava:latest",
        ollama_model="llava:latest",
        enable_provider_fallback=False,
    )
    adapter = GeminiAdapter(config)
    image_path = tmp_path / "figure.png"
    image_path.write_bytes(b"fake-png")

    result = adapter.edit(image_path, "Please recolor the arrows to red")

    assert "not bitmap image editing" in result.error


def test_detect_image_media_type_prefers_magic_bytes_over_hint() -> None:
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"fake-jpeg-payload"

    detected = _detect_image_media_type(jpeg_bytes, hinted_media_type="image/png")

    assert detected == "image/jpeg"


def test_google_parse_response_detects_jpeg_inline_data() -> None:
    config = GeminiConfig(
        provider=GOOGLE_PROVIDER,
        google_api_key="google-key",
        enable_provider_fallback=False,
    )
    adapter = GeminiAdapter(config)

    class InlineData:
        def __init__(self, data: bytes, mime_type: str) -> None:
            self.data = data
            self.mime_type = mime_type

    class Part:
        def __init__(self, data: bytes, mime_type: str) -> None:
            self.inline_data = InlineData(data, mime_type)

    class Response:
        def __init__(self, parts: list[object]) -> None:
            self.parts = parts

    response = Response([Part(b"\xff\xd8\xff\xe0fake-jpeg-payload", "image/png")])

    result = adapter._generation._parse_response(response, "stub-model", 0.0)

    assert result.media_type == "image/jpeg"
    assert result.file_extension == ".jpg"


def test_parse_openrouter_image_response_reports_typed_failure_when_image_missing() -> None:
    payload, failure = parse_openrouter_image_response(
        {"choices": [{"message": {"content": "text only", "images": []}}]}
    )

    assert payload is None
    assert failure is not None
    assert failure.kind is ProviderFailureKind.INVALID_RESPONSE
    assert failure.message == "No image returned by OpenRouter image model"
