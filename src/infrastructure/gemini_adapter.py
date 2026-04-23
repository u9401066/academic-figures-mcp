"""Multi-provider figure adapter with retry, fallback, and local Ollama support."""

from __future__ import annotations

import contextlib
import re
import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, TypeVar, cast

import httpx
from google import genai

from src.domain.entities import GenerationErrorKind, GenerationResult, GenerationResultStatus
from src.domain.interfaces import FigureEvaluator, ImageGenerator, ImageVerifier
from src.domain.value_objects import (
    EVAL_DOMAINS,
    QUALITY_GATE_MIN_SCORE,
    QUALITY_GATE_MIN_TOTAL,
    QualityVerdict,
)
from src.infrastructure.config import OLLAMA_PROVIDER, OPENAI_PROVIDER, OPENROUTER_PROVIDER
from src.infrastructure.gemini_provider_runtimes import (
    ProviderFailure,
    ProviderFailureKind,
    build_provider_runtime,
    detect_image_media_type,
    parse_google_image_response,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from src.infrastructure.config import GeminiConfig

T = TypeVar("T")


def _detect_image_media_type(image_bytes: bytes, *, hinted_media_type: str | None = None) -> str:
    return detect_image_media_type(image_bytes, hinted_media_type=hinted_media_type)


class _GeminiProviderSupport:
    """Shared provider runtime helpers for generation, editing, and evaluation."""

    def __init__(self, config: GeminiConfig) -> None:
        self._config = config
        self._client = None if not config.is_google else genai.Client(api_key=config.api_key)

    def _resolve_model_name(self, model: str | None) -> str:
        if model == "high_fidelity":
            return self._config.high_fidelity_model
        if model == "low_latency":
            return self._config.low_latency_model
        return model or self._config.default_model

    def create_edit_session(self, *, model: str | None = None) -> EditSession:
        model_name = model or self._config.default_model
        if not self._config.is_google:
            raise ValueError(
                "Multi-turn edit sessions are only supported for the direct Google provider."
            )
        chat = self._google_client().chats.create(model=model_name)
        return EditSession(chat=chat, model=model_name)

    def _request_json_with_retry(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, object],
    ) -> tuple[dict[str, object] | None, ProviderFailure | None]:
        response, failure = self._call_with_retry(
            lambda: httpx.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self._config.request_timeout_seconds,
            )
        )
        if failure is not None or response is None:
            return None, failure

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return None, self._failure_from_http_status(exc)

        try:
            data = response.json()
        except ValueError as exc:
            return None, ProviderFailure(
                kind=ProviderFailureKind.INVALID_RESPONSE,
                message=str(exc),
            )
        if not isinstance(data, dict):
            return None, ProviderFailure(
                kind=ProviderFailureKind.INVALID_RESPONSE,
                message="Provider returned non-object JSON payload",
            )
        return data, None

    def _request_multipart_with_retry(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        data: dict[str, str],
        files: list[tuple[str, tuple[str, bytes, str]]],
    ) -> tuple[dict[str, object] | None, ProviderFailure | None]:
        response, failure = self._call_with_retry(
            lambda: httpx.post(
                endpoint,
                headers=headers,
                data=data,
                files=cast("Any", files),
                timeout=self._config.request_timeout_seconds,
            )
        )
        if failure is not None or response is None:
            return None, failure

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return None, self._failure_from_http_status(exc)

        try:
            payload = response.json()
        except ValueError as exc:
            return None, ProviderFailure(
                kind=ProviderFailureKind.INVALID_RESPONSE,
                message=str(exc),
            )
        if not isinstance(payload, dict):
            return None, ProviderFailure(
                kind=ProviderFailureKind.INVALID_RESPONSE,
                message="Provider returned non-object JSON payload",
            )
        return payload, None

    def _call_with_retry(
        self,
        operation: Callable[[], T],
    ) -> tuple[T | None, ProviderFailure | None]:
        last_failure: ProviderFailure | None = None
        for attempt in range(1, self._config.max_attempts + 1):
            try:
                return operation(), None
            except Exception as exc:
                last_failure = self._failure_from_exception(exc)
                if attempt >= self._config.max_attempts or not last_failure.retryable:
                    break
                time.sleep(self._retry_delay(attempt))
        return None, last_failure or ProviderFailure(
            kind=ProviderFailureKind.PERMANENT,
            message="Unknown provider error",
        )

    def _retry_delay(self, attempt: int) -> float:
        return float(min(self._config.retry_backoff_seconds * (2 ** max(0, attempt - 1)), 8.0))

    def _failure_from_exception(self, exc: Exception) -> ProviderFailure:
        if isinstance(
            exc,
            (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.RemoteProtocolError,
            ),
        ):
            return ProviderFailure(
                kind=ProviderFailureKind.TRANSIENT,
                message=str(exc),
            )
        if isinstance(exc, httpx.HTTPStatusError):
            return self._failure_from_http_status(exc)

        lowered = str(exc).lower()
        if any(
            token in lowered
            for token in (
                "429",
                "quota",
                "rate limit",
                "resource_exhausted",
                "temporarily unavailable",
                "timed out",
                "timeout",
                "connection reset",
                "503",
                "502",
                "500",
            )
        ):
            return ProviderFailure(
                kind=ProviderFailureKind.TRANSIENT,
                message=str(exc),
            )
        return ProviderFailure(
            kind=ProviderFailureKind.PERMANENT,
            message=str(exc),
        )

    def _failure_from_http_status(self, exc: httpx.HTTPStatusError) -> ProviderFailure:
        status_code = exc.response.status_code
        kind = (
            ProviderFailureKind.TRANSIENT
            if status_code in {408, 409, 425, 429, 500, 502, 503, 504}
            else ProviderFailureKind.PERMANENT
        )
        return ProviderFailure(kind=kind, message=str(exc))

    def _fallback_config(self, fallback_provider: str) -> GeminiConfig:
        return replace(
            self._config,
            provider=fallback_provider,
            default_model=self._provider_default_model(fallback_provider),
            high_fidelity_model=self._provider_high_fidelity_model(fallback_provider),
            low_latency_model=self._provider_low_latency_model(fallback_provider),
            enable_provider_fallback=False,
        )

    def _provider_default_model(self, provider: str) -> str:
        if provider == OPENROUTER_PROVIDER:
            return "google/gemini-3.1-flash-image-preview"
        if provider == OPENAI_PROVIDER:
            return "gpt-image-2"
        if provider == OLLAMA_PROVIDER:
            return self._config.ollama_model
        return "gemini-3.1-flash-image-preview"

    def _provider_high_fidelity_model(self, provider: str) -> str:
        if provider == OPENROUTER_PROVIDER:
            return "google/gemini-3-pro-image-preview"
        if provider == OPENAI_PROVIDER:
            return "gpt-image-2"
        if provider == OLLAMA_PROVIDER:
            return self._config.ollama_model
        return "gemini-3-pro-image-preview"

    def _provider_low_latency_model(self, provider: str) -> str:
        if provider == OPENROUTER_PROVIDER:
            return "google/gemini-2.5-flash-image"
        if provider == OPENAI_PROVIDER:
            return "gpt-image-2"
        if provider == OLLAMA_PROVIDER:
            return self._config.ollama_model
        return "gemini-2.5-flash-image"

    def _google_client(self) -> genai.Client:
        if self._client is None:
            raise RuntimeError("Google Gemini client is unavailable for the active provider.")
        return self._client

    def _openrouter_endpoint(self) -> str:
        base_url = self._config.openrouter_base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _ollama_endpoint(self) -> str:
        base_url = self._config.ollama_base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    def _openai_images_generation_endpoint(self) -> str:
        return self._openai_endpoint("images/generations")

    def _openai_images_edit_endpoint(self) -> str:
        return self._openai_endpoint("images/edits")

    def _openai_responses_endpoint(self) -> str:
        return self._openai_endpoint("responses")

    def _openai_endpoint(self, path: str) -> str:
        base_url = self._config.openai_base_url.rstrip("/")
        normalized_path = path.lstrip("/")
        if base_url.endswith(f"/{normalized_path}"):
            return base_url
        return f"{base_url}/{normalized_path}"

    def _openrouter_headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        if self._config.openrouter_http_referer:
            headers["HTTP-Referer"] = self._config.openrouter_http_referer
        if self._config.openrouter_app_title:
            headers["X-OpenRouter-Title"] = self._config.openrouter_app_title
        return headers

    def _openai_headers(self, *, json_content_type: bool = True) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._config.api_key}"}
        if json_content_type:
            headers["Content-Type"] = "application/json"
        return headers

    def _openrouter_image_config(self, aspect_ratio: str) -> dict[str, str]:
        config = {"aspect_ratio": aspect_ratio}
        image_size = self._normalize_openrouter_image_size(self._config.default_image_size)
        if image_size:
            config["image_size"] = image_size
        return config

    def _google_image_size(self) -> str | None:
        valid = {"512", "1K", "2K", "4K"}
        image_size = self._config.default_image_size.strip()
        return image_size if image_size in valid else None

    def _openai_image_options(
        self,
        *,
        output_size: str | None = None,
    ) -> dict[str, str]:
        size = self._normalize_openai_image_size(output_size or self._config.openai_image_size)
        quality = self._normalize_openai_option(
            self._config.openai_quality,
            {"auto", "low", "medium", "high"},
            default="auto",
        )
        background = self._normalize_openai_option(
            self._config.openai_background,
            {"auto", "opaque", "transparent"},
            default="auto",
        )
        output_format = self._normalize_openai_option(
            self._config.openai_output_format,
            {"png", "jpeg", "jpg", "webp"},
            default="png",
        )
        if output_format == "jpg":
            output_format = "jpeg"
        if output_format == "jpeg" and background == "transparent":
            background = "auto"
        return {
            "size": size,
            "quality": quality,
            "background": background,
            "output_format": output_format,
        }

    def _openai_vision_model(self) -> str:
        return self._config.openai_vision_model.strip() or "gpt-5.4-mini"

    def _normalize_openrouter_image_size(self, value: str) -> str | None:
        aliases = {
            "0.5k": "0.5K",
            "512": "0.5K",
            "1k": "1K",
            "1024": "1K",
            "1024x1536": "1K",
            "2k": "2K",
            "2048": "2K",
            "4k": "4K",
            "4096": "4K",
        }
        return aliases.get(value.strip().lower())

    def _normalize_openai_image_size(self, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized or normalized == "auto":
            return "auto"
        match = re.match(r"^(\d{2,5})x(\d{2,5})$", normalized)
        if match is None:
            return "auto"
        width = int(match.group(1))
        height = int(match.group(2))
        if width <= 0 or height <= 0 or max(width, height) > 3840:
            return "auto"
        return f"{width}x{height}"

    @staticmethod
    def _normalize_openai_option(
        value: str,
        allowed: set[str],
        *,
        default: str,
    ) -> str:
        normalized = value.strip().lower()
        return normalized if normalized in allowed else default

    def _result_from_failure(
        self,
        *,
        model_name: str,
        start: float,
        failure: ProviderFailure,
    ) -> GenerationResult:
        return GenerationResult(
            model=model_name,
            elapsed_seconds=round(time.time() - start, 2),
            error=failure.message,
            status=GenerationResultStatus.FAILED,
            error_kind=GenerationErrorKind(failure.kind.value),
        )

    def _parse_response(
        self,
        response: object,
        model_name: str,
        start: float,
    ) -> GenerationResult:
        image_bytes: bytes | None = None
        hinted_media_type: str | None = None
        text_parts: list[str] = []

        for part in self._response_parts(response):
            inline_data = getattr(part, "inline_data", None)
            if inline_data is not None:
                image_bytes = inline_data.data
                hinted_media_type = getattr(inline_data, "mime_type", None)
            elif getattr(part, "text", None) is not None:
                text_parts.append(part.text)

        elapsed = time.time() - start
        if image_bytes is None:
            return GenerationResult(
                model=model_name,
                text="\n".join(text_parts),
                elapsed_seconds=round(elapsed, 2),
                error="No image returned by model",
            )

        return GenerationResult(
            image_bytes=image_bytes,
            text="\n".join(text_parts),
            model=model_name,
            elapsed_seconds=round(elapsed, 2),
            media_type=_detect_image_media_type(image_bytes, hinted_media_type=hinted_media_type),
        )

    def _response_parts(self, response: object) -> list[Any]:
        return list(getattr(response, "parts", []) or [])

    def _extract_response_text(self, response: object) -> str:
        text_parts: list[str] = []
        for part in self._response_parts(response):
            if getattr(part, "text", None) is not None:
                text_parts.append(part.text)
        return "\n".join(text_parts).strip()


class GeminiFallbackRouter(_GeminiProviderSupport):
    """Owns provider fallback selection away from generation/edit adapters."""

    def _fallback_config_for(self, failure: ProviderFailure) -> GeminiConfig | None:
        fallback_provider = self._config.fallback_provider
        if fallback_provider is None or not failure.retryable:
            return None
        return self._fallback_config(fallback_provider)

    def maybe_generate(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        output_size: str | None,
        failure: ProviderFailure,
    ) -> GenerationResult | None:
        fallback_config = self._fallback_config_for(failure)
        if fallback_config is None:
            return None
        return GeminiGenerationAdapter(fallback_config).generate(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            output_size=output_size,
        )

    def maybe_edit(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        failure: ProviderFailure,
    ) -> GenerationResult | None:
        fallback_config = self._fallback_config_for(failure)
        if fallback_config is None:
            return None

        import tempfile
        from pathlib import Path

        temp_suffix = ".png" if mime_type == "image/png" else ".jpg"
        with tempfile.NamedTemporaryFile(suffix=temp_suffix, delete=False) as handle:
            handle.write(image_bytes)
            temp_path = Path(handle.name)
        try:
            return GeminiEditAdapter(fallback_config).edit(temp_path, instruction)
        finally:
            with contextlib.suppress(OSError):
                temp_path.unlink(missing_ok=True)


class GeminiGenerationAdapter(_GeminiProviderSupport):
    """Generation-only adapter for image and local SVG output."""

    def __init__(self, config: GeminiConfig) -> None:
        super().__init__(config)
        self._fallback_router = GeminiFallbackRouter(config)
        self._runtime = build_provider_runtime(self)

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        aspect_ratio: str | None = None,
        output_size: str | None = None,
    ) -> GenerationResult:
        model_name = self._resolve_model_name(model)
        ar = aspect_ratio or self._config.default_aspect_ratio
        start = time.time()
        outcome = self._runtime.generate(
            prompt=prompt,
            model_name=model_name,
            aspect_ratio=ar,
            output_size=output_size,
            start=start,
        )
        if outcome.result is not None:
            return outcome.result

        failure = outcome.failure or ProviderFailure(
            kind=ProviderFailureKind.PERMANENT,
            message="Provider generation failed",
        )
        fallback = self._fallback_router.maybe_generate(
            prompt=prompt,
            aspect_ratio=ar,
            output_size=output_size,
            failure=failure,
        )
        if fallback is not None:
            return fallback
        return self._result_from_failure(model_name=model_name, start=start, failure=failure)

    def _parse_response(
        self,
        response: object,
        model_name: str,
        start: float,
    ) -> GenerationResult:
        payload, failure = parse_google_image_response(response)
        if failure is not None or payload is None:
            return self._result_from_failure(
                model_name=model_name,
                start=start,
                failure=failure
                or ProviderFailure(
                    kind=ProviderFailureKind.INVALID_RESPONSE,
                    message="No image returned by model",
                ),
            )
        return GenerationResult(
            image_bytes=payload.image_bytes,
            text=payload.text,
            model=model_name,
            elapsed_seconds=round(time.time() - start, 2),
            media_type=payload.media_type,
        )


class GeminiEditAdapter(_GeminiProviderSupport):
    """Edit-only adapter for provider-backed image modification flows."""

    def __init__(self, config: GeminiConfig) -> None:
        super().__init__(config)
        self._fallback_router = GeminiFallbackRouter(config)
        self._runtime = build_provider_runtime(self)

    def edit(
        self,
        image_path: Path,
        instruction: str,
        *,
        model: str | None = None,
    ) -> GenerationResult:
        model_name = model or self._config.default_model
        start = time.time()

        if not image_path.exists():
            return self._result_from_failure(
                model_name=model_name,
                start=start,
                failure=ProviderFailure(
                    kind=ProviderFailureKind.NOT_FOUND,
                    message=f"Image not found: {image_path}",
                ),
            )

        img_bytes = image_path.read_bytes()
        suffix_hint = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        mime = _detect_image_media_type(img_bytes, hinted_media_type=suffix_hint)

        outcome = self._runtime.edit(
            image_bytes=img_bytes,
            mime_type=mime,
            instruction=instruction,
            model_name=model_name,
            start=start,
        )
        if outcome.result is not None:
            return outcome.result

        failure = outcome.failure or ProviderFailure(
            kind=ProviderFailureKind.PERMANENT,
            message="Provider edit failed",
        )
        fallback = self._fallback_router.maybe_edit(
            image_bytes=img_bytes,
            mime_type=mime,
            instruction=instruction,
            failure=failure,
        )
        if fallback is not None:
            return fallback
        return self._result_from_failure(model_name=model_name, start=start, failure=failure)


class GeminiAdapter(ImageGenerator):
    """Facade that composes generation and edit adapters."""

    def __init__(self, config: GeminiConfig) -> None:
        self._config = config
        self._generation = GeminiGenerationAdapter(config)
        self._editing = GeminiEditAdapter(config)

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        aspect_ratio: str | None = None,
        output_size: str | None = None,
    ) -> GenerationResult:
        return self._generation.generate(
            prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            output_size=output_size,
        )

    def edit(
        self,
        image_path: Path,
        instruction: str,
        *,
        model: str | None = None,
    ) -> GenerationResult:
        return self._editing.edit(image_path, instruction, model=model)

    def create_edit_session(self, *, model: str | None = None) -> EditSession:
        return self._editing.create_edit_session(model=model)

    def _parse_response(
        self,
        response: object,
        model_name: str,
        start: float,
    ) -> GenerationResult:
        return self._generation._parse_response(response, model_name, start)


@dataclass
class EditSession:
    """Multi-turn editing session backed by Gemini chat."""

    chat: Any
    model: str
    turns: int = 0

    def send(self, instruction: str) -> GenerationResult:
        start = time.time()
        try:
            response = self.chat.send_message(instruction)
        except Exception as exc:
            return GenerationResult(
                model=self.model,
                elapsed_seconds=time.time() - start,
                error=str(exc),
            )

        self.turns += 1

        payload, failure = parse_google_image_response(response)
        if failure is not None or payload is None:
            return GenerationResult(
                model=self.model,
                elapsed_seconds=round(time.time() - start, 2),
                error=(
                    failure
                    or ProviderFailure(
                        kind=ProviderFailureKind.INVALID_RESPONSE,
                        message="No image returned",
                    )
                ).message,
            )

        return GenerationResult(
            image_bytes=payload.image_bytes,
            text=payload.text,
            model=self.model,
            elapsed_seconds=round(time.time() - start, 2),
            media_type=payload.media_type,
        )


class GeminiFigureEvaluator(_GeminiProviderSupport, FigureEvaluator):
    """Dedicated textual evaluation adapter for existing figure assets."""

    def __init__(self, config: GeminiConfig) -> None:
        super().__init__(config)
        self._runtime = build_provider_runtime(self)

    def evaluate(
        self,
        image_path: Path,
        instruction: str,
        *,
        model: str | None = None,
    ) -> GenerationResult:
        model_name = self._resolve_model_name(model)
        start = time.time()

        if not image_path.exists():
            return self._result_from_failure(
                model_name=model_name,
                start=start,
                failure=ProviderFailure(
                    kind=ProviderFailureKind.NOT_FOUND,
                    message=f"Image not found: {image_path}",
                ),
            )

        image_bytes = image_path.read_bytes()
        suffix_hint = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        mime_type = _detect_image_media_type(image_bytes, hinted_media_type=suffix_hint)

        outcome = self._runtime.evaluate(
            image_bytes=image_bytes,
            mime_type=mime_type,
            instruction=instruction,
            model_name=model_name,
            start=start,
        )
        if outcome.result is not None:
            return outcome.result
        return self._result_from_failure(
            model_name=model_name,
            start=start,
            failure=outcome.failure
            or ProviderFailure(
                kind=ProviderFailureKind.PERMANENT,
                message="Provider evaluation failed",
            ),
        )


class GeminiImageVerifier(_GeminiProviderSupport, ImageVerifier):
    """Vision-based quality gate using Gemini to verify generated figures."""

    def __init__(self, config: GeminiConfig) -> None:
        super().__init__(config)
        self._runtime = build_provider_runtime(self)

    def verify(
        self,
        image_bytes: bytes,
        *,
        expected_labels: list[str],
        figure_type: str,
        language: str,
    ) -> QualityVerdict:
        mime = _detect_image_media_type(image_bytes)

        label_block = ""
        if expected_labels:
            numbered = "\n".join(
                f"  {i}. 「{label}」" for i, label in enumerate(expected_labels, 1)
            )
            label_block = (
                f"\n\nEXPECTED LABELS (check each one is present and correct):\n"
                f"{numbered}\n"
                f"For each label, report: FOUND_EXACT / FOUND_GARBLED / MISSING"
            )

        verification_prompt = (
            f"You are a quality-gate reviewer for a {figure_type} academic figure.\n"
            f"Target language: {language}\n\n"
            "Score this figure on each of the following 8 domains (1-5 scale):\n"
            + "\n".join(f"- {d}" for d in EVAL_DOMAINS)
            + "\n\nFor each domain, output exactly: DOMAIN: SCORE JUSTIFICATION"
            + label_block
            + "\n\nFinally, list any CRITICAL issues that would block publication."
            + "\n\nFormat your response as structured text."
        )

        outcome = self._runtime.evaluate(
            image_bytes=image_bytes,
            mime_type=mime,
            instruction=verification_prompt,
            model_name=self._config.default_model,
            start=time.time(),
        )
        if outcome.result is not None:
            verification_text = outcome.result.text
        else:
            failure = outcome.failure or ProviderFailure(
                kind=ProviderFailureKind.PERMANENT,
                message="Vision verification failed",
            )
            verification_text = f"Vision verification failed: {failure.message}"

        return self._parse_verdict(
            text=verification_text,
            expected_labels=expected_labels,
        )

    @staticmethod
    def _parse_verdict(
        text: str,
        expected_labels: list[str],
    ) -> QualityVerdict:
        import re as _re

        domain_scores: dict[str, float] = {}
        for domain in EVAL_DOMAINS:
            pattern = _re.compile(rf"{_re.escape(domain)}[:\s]+(\d(?:\.\d)?)", _re.IGNORECASE)
            match = pattern.search(text)
            if match:
                domain_scores[domain] = float(match.group(1))
            else:
                domain_scores[domain] = 0.0

        total = sum(domain_scores.values())

        # Check label status
        missing: list[str] = []
        text_ok = True
        lowered = text.lower()
        for label in expected_labels:
            if ("missing" in lowered and label.lower() in lowered) or (
                "garbled" in lowered and label.lower() in lowered
            ):
                missing.append(label)
                text_ok = False

        # Extract critical issues
        critical: list[str] = []
        if "critical" in lowered:
            for line in text.split("\n"):
                if "critical" in line.lower() and len(line.strip()) > 10:
                    critical.append(line.strip())

        passed = (
            total >= QUALITY_GATE_MIN_TOTAL
            and all(s >= QUALITY_GATE_MIN_SCORE for s in domain_scores.values())
            and text_ok
            and len(critical) == 0
        )

        return QualityVerdict(
            passed=passed,
            domain_scores=domain_scores,
            total_score=total,
            critical_issues=tuple(critical),
            text_verification_passed=text_ok if expected_labels else None,
            missing_labels=tuple(missing),
            summary=text[:500],
        )
