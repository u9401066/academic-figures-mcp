"""Provider-specific runtimes and typed contracts for Gemini adapter flows."""

from __future__ import annotations

import base64
import binascii
import json
import re
import time
from dataclasses import dataclass
from enum import Enum
from html import escape as escape_xml
from textwrap import wrap
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

from google.genai import types

from src.domain.entities import GenerationResult
from src.infrastructure.config import (
    GOOGLE_PROVIDER,
    OLLAMA_PROVIDER,
    OPENAI_PROVIDER,
    OPENROUTER_PROVIDER,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.infrastructure.config import GeminiConfig

T = TypeVar("T")

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"
_GIF_SIGNATURES = (b"GIF87a", b"GIF89a")


class ProviderFailureKind(Enum):
    """Typed runtime failure classes used inside adapter boundaries."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    INVALID_RESPONSE = "invalid_response"
    UNSUPPORTED = "unsupported"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class ProviderFailure:
    """Structured provider/runtime failure passed between adapter layers."""

    kind: ProviderFailureKind
    message: str

    @property
    def retryable(self) -> bool:
        return self.kind is ProviderFailureKind.TRANSIENT


@dataclass(frozen=True)
class ProviderImagePayload:
    """Successful provider payload containing rendered image bytes and text."""

    image_bytes: bytes
    text: str = ""
    media_type: str = "image/png"


@dataclass(frozen=True)
class RuntimeOutcome:
    """Typed adapter/runtime boundary result."""

    result: GenerationResult | None = None
    failure: ProviderFailure | None = None

    @classmethod
    def success(cls, result: GenerationResult) -> RuntimeOutcome:
        return cls(result=result)

    @classmethod
    def failed(cls, failure: ProviderFailure) -> RuntimeOutcome:
        return cls(failure=failure)


@dataclass(frozen=True)
class OllamaBriefSection:
    """Structured section for local Ollama SVG rendering."""

    heading: str
    bullets: tuple[str, ...]


@dataclass(frozen=True)
class OllamaFigureBrief:
    """Typed local figure brief returned by Ollama or prompt heuristics."""

    title: str
    subtitle: str
    sections: tuple[OllamaBriefSection, ...]
    footer: str
    accent_color: str


class ProviderSupport(Protocol):
    """Support hooks implemented by Gemini adapter infrastructure."""

    _config: GeminiConfig

    def _call_with_retry(
        self,
        operation: Callable[[], T],
    ) -> tuple[T | None, ProviderFailure | None]: ...

    def _request_json_with_retry(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, object],
    ) -> tuple[dict[str, object] | None, ProviderFailure | None]: ...

    def _request_multipart_with_retry(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        data: dict[str, str],
        files: list[tuple[str, tuple[str, bytes, str]]],
    ) -> tuple[dict[str, object] | None, ProviderFailure | None]: ...

    def _google_client(self) -> Any: ...

    def _openrouter_endpoint(self) -> str: ...

    def _ollama_endpoint(self) -> str: ...

    def _openai_images_generation_endpoint(self) -> str: ...

    def _openai_images_edit_endpoint(self) -> str: ...

    def _openai_responses_endpoint(self) -> str: ...

    def _openrouter_headers(self) -> dict[str, str]: ...

    def _openai_headers(self, *, json_content_type: bool = True) -> dict[str, str]: ...

    def _openrouter_image_config(self, aspect_ratio: str) -> dict[str, str]: ...

    def _google_image_size(self) -> str | None: ...

    def _openai_image_options(
        self,
        *,
        output_size: str | None = None,
    ) -> dict[str, str]: ...

    def _openai_vision_model(self) -> str: ...


class ProviderRuntime(Protocol):
    """Provider runtime surface consumed by adapters."""

    def generate(
        self,
        *,
        prompt: str,
        model_name: str,
        aspect_ratio: str,
        output_size: str | None,
        start: float,
    ) -> RuntimeOutcome: ...

    def edit(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> RuntimeOutcome: ...

    def evaluate(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> RuntimeOutcome: ...


def detect_image_media_type(image_bytes: bytes, *, hinted_media_type: str | None = None) -> str:
    """Infer media type from image bytes, preferring magic bytes over hints."""

    normalized_hint = _normalize_image_media_type(hinted_media_type)
    stripped = image_bytes.lstrip()

    if image_bytes.startswith(_PNG_SIGNATURE):
        return "image/png"
    if image_bytes.startswith(_JPEG_SIGNATURE):
        return "image/jpeg"
    if any(image_bytes.startswith(signature) for signature in _GIF_SIGNATURES):
        return "image/gif"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    if stripped.startswith(b"<svg") or (
        stripped.startswith(b"<?xml") and b"<svg" in stripped[:512]
    ):
        return "image/svg+xml"
    if normalized_hint is not None:
        return normalized_hint
    return "image/png"


def parse_google_image_response(
    response: types.GenerateContentResponse | Any,
) -> tuple[ProviderImagePayload | None, ProviderFailure | None]:
    """Extract image/text payload from a Google multimodal response."""

    image_bytes: bytes | None = None
    hinted_media_type: str | None = None
    text_parts: list[str] = []

    for part in _response_parts(response):
        inline_data = getattr(part, "inline_data", None)
        if inline_data is not None:
            image_bytes = inline_data.data
            hinted_media_type = getattr(inline_data, "mime_type", None)
        elif getattr(part, "text", None) is not None:
            text_parts.append(part.text)

    if image_bytes is None:
        return None, ProviderFailure(
            kind=ProviderFailureKind.INVALID_RESPONSE,
            message="No image returned by model",
        )

    return (
        ProviderImagePayload(
            image_bytes=image_bytes,
            text="\n".join(text_parts),
            media_type=detect_image_media_type(
                image_bytes,
                hinted_media_type=hinted_media_type,
            ),
        ),
        None,
    )


def extract_google_response_text(response: types.GenerateContentResponse | Any) -> str:
    """Extract textual content from a Google response."""

    text_parts: list[str] = []
    for part in _response_parts(response):
        if getattr(part, "text", None) is not None:
            text_parts.append(part.text)
    return "\n".join(text_parts).strip()


def parse_openrouter_image_response(
    data: dict[str, object],
) -> tuple[ProviderImagePayload | None, ProviderFailure | None]:
    """Extract image/text payload from an OpenRouter image response."""

    text = _extract_message_text(data)

    image_bytes: bytes | None = None
    hinted_media_type: str | None = None
    raw_choices = data.get("choices")
    choices = raw_choices if isinstance(raw_choices, list) else []
    first_choice = choices[0] if choices else {}
    choice = first_choice if isinstance(first_choice, dict) else {}
    raw_message = choice.get("message", {})
    message = raw_message if isinstance(raw_message, dict) else {}
    raw_images = message.get("images", [])
    images = raw_images if isinstance(raw_images, list) else []
    for raw_image in images:
        image = raw_image if isinstance(raw_image, dict) else {}
        raw_image_url = image.get("image_url", {})
        image_url_data = raw_image_url if isinstance(raw_image_url, dict) else {}
        raw_image_url_alt = image.get("imageUrl", {})
        image_url_alt = raw_image_url_alt if isinstance(raw_image_url_alt, dict) else {}
        image_url = image_url_data.get("url") or image_url_alt.get("url")
        if isinstance(image_url, str) and image_url.startswith("data:"):
            try:
                header, encoded = image_url.split(",", 1)
                hinted_media_type = header[5:].split(";", 1)[0]
                image_bytes = base64.b64decode(encoded)
                break
            except Exception:
                image_bytes = None

    if image_bytes is None:
        return None, ProviderFailure(
            kind=ProviderFailureKind.INVALID_RESPONSE,
            message="No image returned by OpenRouter image model",
        )

    return (
        ProviderImagePayload(
            image_bytes=image_bytes,
            text=text,
            media_type=detect_image_media_type(
                image_bytes,
                hinted_media_type=hinted_media_type,
            ),
        ),
        None,
    )


def parse_openrouter_text_response(
    data: dict[str, object],
    *,
    provider_label: str,
) -> tuple[str | None, ProviderFailure | None]:
    """Extract text payload from an OpenRouter-compatible response."""

    text = _extract_message_text(data).strip()
    if text:
        return text, None
    return None, ProviderFailure(
        kind=ProviderFailureKind.INVALID_RESPONSE,
        message=f"No evaluation returned by {provider_label} provider",
    )


def parse_openai_image_response(
    data: dict[str, object],
    *,
    hinted_media_type: str | None = None,
) -> tuple[ProviderImagePayload | None, ProviderFailure | None]:
    """Extract base64 image bytes from an OpenAI Images API response."""

    raw_items = data.get("data")
    items = raw_items if isinstance(raw_items, list) else []
    first_item = items[0] if items else {}
    item = first_item if isinstance(first_item, dict) else {}
    encoded = item.get("b64_json")
    if not isinstance(encoded, str) or not encoded.strip():
        return None, ProviderFailure(
            kind=ProviderFailureKind.INVALID_RESPONSE,
            message="No base64 image returned by OpenAI image model",
        )

    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        return None, ProviderFailure(
            kind=ProviderFailureKind.INVALID_RESPONSE,
            message=f"Invalid base64 image returned by OpenAI image model: {exc}",
        )

    revised_prompt = item.get("revised_prompt")
    text = revised_prompt if isinstance(revised_prompt, str) else ""
    return (
        ProviderImagePayload(
            image_bytes=image_bytes,
            text=text,
            media_type=detect_image_media_type(
                image_bytes,
                hinted_media_type=hinted_media_type,
            ),
        ),
        None,
    )


def parse_openai_text_response(
    data: dict[str, object],
) -> tuple[str | None, ProviderFailure | None]:
    """Extract textual output from an OpenAI Responses API payload."""

    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip(), None

    text_parts = _openai_output_text_parts(data)
    text = "\n".join(part for part in text_parts if part.strip()).strip()
    if text:
        return text, None
    return None, ProviderFailure(
        kind=ProviderFailureKind.INVALID_RESPONSE,
        message="No evaluation returned by OpenAI vision model",
    )


def image_result_from_payload(
    *,
    payload: ProviderImagePayload,
    model_name: str,
    start: float,
) -> GenerationResult:
    """Convert a typed provider image payload into a domain result."""

    return GenerationResult(
        image_bytes=payload.image_bytes,
        text=payload.text,
        model=model_name,
        elapsed_seconds=round(time.time() - start, 2),
        media_type=payload.media_type,
    )


def text_result(*, text: str, model_name: str, start: float) -> GenerationResult:
    """Convert provider text into a domain result."""

    return GenerationResult(
        text=text,
        model=model_name,
        elapsed_seconds=round(time.time() - start, 2),
    )


class GoogleProviderRuntime:
    """Google-specific runtime for generation, edit, and evaluation."""

    def __init__(self, support: ProviderSupport) -> None:
        self._support = support

    def generate(
        self,
        *,
        prompt: str,
        model_name: str,
        aspect_ratio: str,
        output_size: str | None,
        start: float,
    ) -> RuntimeOutcome:
        del output_size

        image_config: dict[str, str] = {"aspect_ratio": aspect_ratio}
        image_size = self._support._google_image_size()
        if image_size:
            image_config["image_size"] = image_size

        response, failure = self._support._call_with_retry(
            lambda: self._support._google_client().models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=cast("Any", image_config),
                ),
            )
        )
        if failure is not None or response is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.PERMANENT,
                    message="Google provider failed",
                )
            )

        payload, failure = parse_google_image_response(response)
        if failure is not None or payload is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.INVALID_RESPONSE,
                    message="No image returned by model",
                )
            )
        return RuntimeOutcome.success(
            image_result_from_payload(payload=payload, model_name=model_name, start=start)
        )

    def edit(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> RuntimeOutcome:
        response, failure = self._support._call_with_retry(
            lambda: self._support._google_client().models.generate_content(
                model=model_name,
                contents=cast(
                    "Any",
                    [instruction, types.Part.from_bytes(data=image_bytes, mime_type=mime_type)],
                ),
                config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
            )
        )
        if failure is not None or response is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.PERMANENT,
                    message="Google provider failed",
                )
            )

        payload, failure = parse_google_image_response(response)
        if failure is not None or payload is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.INVALID_RESPONSE,
                    message="No image returned by model",
                )
            )
        return RuntimeOutcome.success(
            image_result_from_payload(payload=payload, model_name=model_name, start=start)
        )

    def evaluate(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> RuntimeOutcome:
        response, failure = self._support._call_with_retry(
            lambda: self._support._google_client().models.generate_content(
                model=model_name,
                contents=cast(
                    "Any",
                    [instruction, types.Part.from_bytes(data=image_bytes, mime_type=mime_type)],
                ),
                config=types.GenerateContentConfig(response_modalities=["TEXT"]),
            )
        )
        if failure is not None or response is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.PERMANENT,
                    message="Google provider failed",
                )
            )

        text = extract_google_response_text(response)
        if not text:
            return RuntimeOutcome.failed(
                ProviderFailure(
                    kind=ProviderFailureKind.INVALID_RESPONSE,
                    message="No evaluation returned by Google provider",
                )
            )
        return RuntimeOutcome.success(text_result(text=text, model_name=model_name, start=start))


class OpenRouterProviderRuntime:
    """OpenRouter-specific runtime for generation, edit, and evaluation."""

    def __init__(self, support: ProviderSupport) -> None:
        self._support = support

    def generate(
        self,
        *,
        prompt: str,
        model_name: str,
        aspect_ratio: str,
        output_size: str | None,
        start: float,
    ) -> RuntimeOutcome:
        del output_size

        payload: dict[str, object] = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
            "image_config": self._support._openrouter_image_config(aspect_ratio),
        }
        data, failure = self._support._request_json_with_retry(
            endpoint=self._support._openrouter_endpoint(),
            headers=self._support._openrouter_headers(),
            payload=payload,
        )
        if failure is not None or data is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.PERMANENT,
                    message="OpenRouter provider failed",
                )
            )

        parsed, failure = parse_openrouter_image_response(data)
        if failure is not None or parsed is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.INVALID_RESPONSE,
                    message="No image returned by OpenRouter image model",
                )
            )
        return RuntimeOutcome.success(
            image_result_from_payload(payload=parsed, model_name=model_name, start=start)
        )

    def edit(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> RuntimeOutcome:
        image_data_url = _data_url_for_image(image_bytes=image_bytes, mime_type=mime_type)
        payload: dict[str, object] = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                }
            ],
            "modalities": ["image", "text"],
            "image_config": self._support._openrouter_image_config(
                self._support._config.default_aspect_ratio
            ),
        }
        data, failure = self._support._request_json_with_retry(
            endpoint=self._support._openrouter_endpoint(),
            headers=self._support._openrouter_headers(),
            payload=payload,
        )
        if failure is not None or data is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.PERMANENT,
                    message="OpenRouter provider failed",
                )
            )

        parsed, failure = parse_openrouter_image_response(data)
        if failure is not None or parsed is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.INVALID_RESPONSE,
                    message="No image returned by OpenRouter image model",
                )
            )
        return RuntimeOutcome.success(
            image_result_from_payload(payload=parsed, model_name=model_name, start=start)
        )

    def evaluate(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> RuntimeOutcome:
        image_data_url = _data_url_for_image(image_bytes=image_bytes, mime_type=mime_type)
        payload: dict[str, object] = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                }
            ],
        }
        data, failure = self._support._request_json_with_retry(
            endpoint=self._support._openrouter_endpoint(),
            headers=self._support._openrouter_headers(),
            payload=payload,
        )
        if failure is not None or data is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.PERMANENT,
                    message="OpenRouter provider failed",
                )
            )

        text, failure = parse_openrouter_text_response(data, provider_label="OpenRouter")
        if failure is not None or text is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.INVALID_RESPONSE,
                    message="No evaluation returned by OpenRouter provider",
                )
            )
        return RuntimeOutcome.success(text_result(text=text, model_name=model_name, start=start))


class OpenAIProviderRuntime:
    """OpenAI runtime for GPT Image generation/editing and vision review."""

    def __init__(self, support: ProviderSupport) -> None:
        self._support = support

    def generate(
        self,
        *,
        prompt: str,
        model_name: str,
        aspect_ratio: str,
        output_size: str | None,
        start: float,
    ) -> RuntimeOutcome:
        del aspect_ratio

        payload: dict[str, object] = {
            "model": model_name,
            "prompt": prompt,
            **self._support._openai_image_options(output_size=output_size),
        }
        data, failure = self._support._request_json_with_retry(
            endpoint=self._support._openai_images_generation_endpoint(),
            headers=self._support._openai_headers(),
            payload=payload,
        )
        if failure is not None or data is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.PERMANENT,
                    message="OpenAI image provider failed",
                )
            )

        parsed, failure = parse_openai_image_response(
            data,
            hinted_media_type=self._hinted_output_media_type(),
        )
        if failure is not None or parsed is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.INVALID_RESPONSE,
                    message="No image returned by OpenAI image model",
                )
            )
        return RuntimeOutcome.success(
            image_result_from_payload(payload=parsed, model_name=model_name, start=start)
        )

    def edit(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> RuntimeOutcome:
        filename = _filename_for_mime_type(mime_type)
        data_fields = {
            "model": model_name,
            "prompt": instruction,
            **self._support._openai_image_options(output_size=None),
        }
        data, failure = self._support._request_multipart_with_retry(
            endpoint=self._support._openai_images_edit_endpoint(),
            headers=self._support._openai_headers(json_content_type=False),
            data=data_fields,
            files=[("image[]", (filename, image_bytes, mime_type))],
        )
        if failure is not None or data is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.PERMANENT,
                    message="OpenAI image edit failed",
                )
            )

        parsed, failure = parse_openai_image_response(
            data,
            hinted_media_type=self._hinted_output_media_type(),
        )
        if failure is not None or parsed is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.INVALID_RESPONSE,
                    message="No image returned by OpenAI image edit model",
                )
            )
        return RuntimeOutcome.success(
            image_result_from_payload(payload=parsed, model_name=model_name, start=start)
        )

    def evaluate(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> RuntimeOutcome:
        del model_name

        image_data_url = _data_url_for_image(image_bytes=image_bytes, mime_type=mime_type)
        vision_model = self._support._openai_vision_model()
        payload: dict[str, object] = {
            "model": vision_model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": instruction},
                        {"type": "input_image", "image_url": image_data_url},
                    ],
                }
            ],
        }
        data, failure = self._support._request_json_with_retry(
            endpoint=self._support._openai_responses_endpoint(),
            headers=self._support._openai_headers(),
            payload=payload,
        )
        if failure is not None or data is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.PERMANENT,
                    message="OpenAI vision provider failed",
                )
            )

        text, failure = parse_openai_text_response(data)
        if failure is not None or text is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.INVALID_RESPONSE,
                    message="No evaluation returned by OpenAI vision model",
                )
            )
        return RuntimeOutcome.success(text_result(text=text, model_name=vision_model, start=start))

    def _hinted_output_media_type(self) -> str:
        normalized = self._support._config.openai_output_format.strip().lower()
        if normalized in {"jpg", "jpeg"}:
            return "image/jpeg"
        if normalized == "webp":
            return "image/webp"
        return "image/png"


class OllamaProviderRuntime:
    """Ollama-specific runtime for local generation and evaluation flows."""

    def __init__(self, support: ProviderSupport) -> None:
        self._support = support

    def generate(
        self,
        *,
        prompt: str,
        model_name: str,
        aspect_ratio: str,
        output_size: str | None,
        start: float,
    ) -> RuntimeOutcome:
        del aspect_ratio, output_size

        text, failure = _ollama_chat(
            support=self._support,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You convert academic figure briefs into strict JSON "
                        "for an SVG renderer. Return JSON only with keys title, "
                        "subtitle, sections, footer, accent_color."
                    ),
                },
                {"role": "user", "content": ollama_generation_instruction(prompt)},
            ],
            model_name=model_name,
        )
        if failure is not None or text is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.PERMANENT,
                    message="Ollama request failed",
                )
            )

        brief = parse_ollama_brief(text) or brief_from_prompt(prompt)
        width, height = extract_canvas_size(prompt)
        svg = render_svg_brief(brief=brief, width=width, height=height)
        return RuntimeOutcome.success(
            GenerationResult(
                image_bytes=svg.encode("utf-8"),
                text=text,
                model=model_name,
                elapsed_seconds=round(time.time() - start, 2),
                media_type="image/svg+xml",
            )
        )

    def edit(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> RuntimeOutcome:
        del image_bytes, mime_type, instruction, start

        return RuntimeOutcome.failed(
            ProviderFailure(
                kind=ProviderFailureKind.UNSUPPORTED,
                message=(
                    "Ollama runtime currently supports planning, local SVG "
                    "generation, and vision-based evaluation, but not bitmap "
                    "image editing."
                ),
            )
        )

    def evaluate(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> RuntimeOutcome:
        image_data_url = _data_url_for_image(image_bytes=image_bytes, mime_type=mime_type)
        text, failure = _ollama_chat(
            support=self._support,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You review academic figures for structure, scientific "
                        "clarity, and publication quality. Return concise scores and issues."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                },
            ],
            model_name=model_name,
        )
        if failure is not None or text is None:
            return RuntimeOutcome.failed(
                failure
                or ProviderFailure(
                    kind=ProviderFailureKind.PERMANENT,
                    message="Ollama request failed",
                )
            )
        if not text.strip():
            return RuntimeOutcome.failed(
                ProviderFailure(
                    kind=ProviderFailureKind.INVALID_RESPONSE,
                    message="No evaluation returned by Ollama provider",
                )
            )
        return RuntimeOutcome.success(text_result(text=text, model_name=model_name, start=start))


def build_provider_runtime(support: ProviderSupport) -> ProviderRuntime:
    """Select the provider-specific runtime implementation for a config."""

    if support._config.provider == OLLAMA_PROVIDER:
        return OllamaProviderRuntime(support)
    if support._config.provider == OPENAI_PROVIDER:
        return OpenAIProviderRuntime(support)
    if support._config.provider == OPENROUTER_PROVIDER:
        return OpenRouterProviderRuntime(support)
    if support._config.provider == GOOGLE_PROVIDER:
        return GoogleProviderRuntime(support)
    raise ValueError(f"Unsupported image provider: {support._config.provider}")


def _normalize_image_media_type(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.split(";", 1)[0].strip().lower()
    if normalized == "image/jpg":
        return "image/jpeg"
    return normalized


def _response_parts(response: types.GenerateContentResponse | Any) -> list[Any]:
    return list(getattr(response, "parts", []) or [])


def _extract_message_text(data: dict[str, object]) -> str:
    raw_choices = data.get("choices")
    choices = raw_choices if isinstance(raw_choices, list) else []
    first_choice = choices[0] if choices else {}
    choice = first_choice if isinstance(first_choice, dict) else {}
    raw_message = choice.get("message", {})
    message = raw_message if isinstance(raw_message, dict) else {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_chunks = []
        for entry in content:
            item = entry if isinstance(entry, dict) else {}
            maybe_text = item.get("text")
            if isinstance(maybe_text, str):
                text_chunks.append(maybe_text)
        return "\n".join(text_chunks)
    return ""


def _openai_output_text_parts(data: dict[str, object]) -> list[str]:
    raw_output = data.get("output")
    output_items = raw_output if isinstance(raw_output, list) else []
    text_parts: list[str] = []
    for raw_item in output_items:
        item = raw_item if isinstance(raw_item, dict) else {}
        raw_content = item.get("content")
        content_items = raw_content if isinstance(raw_content, list) else []
        for raw_content_item in content_items:
            content_item = raw_content_item if isinstance(raw_content_item, dict) else {}
            maybe_text = content_item.get("text")
            if isinstance(maybe_text, str):
                text_parts.append(maybe_text)
    return text_parts


def _filename_for_mime_type(mime_type: str) -> str:
    if mime_type == "image/jpeg":
        return "input.jpg"
    if mime_type == "image/webp":
        return "input.webp"
    return "input.png"


def _ollama_chat(
    *,
    support: ProviderSupport,
    messages: list[dict[str, object]],
    model_name: str,
) -> tuple[str | None, ProviderFailure | None]:
    payload: dict[str, object] = {
        "model": model_name,
        "messages": messages,
    }
    data, failure = support._request_json_with_retry(
        endpoint=support._ollama_endpoint(),
        headers={"Content-Type": "application/json"},
        payload=payload,
    )
    if failure is not None or data is None:
        return None, failure or ProviderFailure(
            kind=ProviderFailureKind.PERMANENT,
            message="Ollama request failed",
        )

    message_text = _extract_message_text(data)
    if not message_text:
        return None, ProviderFailure(
            kind=ProviderFailureKind.INVALID_RESPONSE,
            message="No text returned by Ollama",
        )
    return message_text, None


def ollama_generation_instruction(prompt: str) -> str:
    return (
        "Summarize this academic figure brief into compact JSON. "
        "Create 3 to 5 sections, each with a short heading and 1 to 2 bullets. "
        "Keep all text publication-safe and concise. Return JSON only.\n\n"
        f"{prompt}"
    )


def parse_ollama_brief(text: str) -> OllamaFigureBrief | None:
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return None
    try:
        parsed = json.loads(text[first : last + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None

    raw_sections = parsed.get("sections", [])
    sections_list = raw_sections if isinstance(raw_sections, list) else []
    sections = tuple(
        _coerce_brief_section(item, index)
        for index, item in enumerate(sections_list[:4])
    )
    return OllamaFigureBrief(
        title=str(parsed.get("title", "Academic Figure")),
        subtitle=str(parsed.get("subtitle", "Structured local rendering")),
        sections=sections,
        footer=str(parsed.get("footer", "Academic Figures MCP")),
        accent_color=str(parsed.get("accent_color", "#0F6CBD")),
    )


def brief_from_prompt(prompt: str) -> OllamaFigureBrief:
    title_match = re.search(r"title:\s*'([^']+)'", prompt)
    citation_match = re.search(r"citation:\s*'([^']+)'", prompt)
    sections_match = re.search(r"sections:\s*(.+)", prompt)
    section_tokens: list[str] = []
    if sections_match:
        raw_sections = sections_match.group(1)
        section_tokens = [
            token.strip(" -") for token in re.split(r"→|,", raw_sections) if token.strip()
        ]

    sections = tuple(
        OllamaBriefSection(
            heading=token.title(),
            bullets=("Key information distilled from the academic brief",),
        )
        for token in section_tokens[:4]
    )
    if not sections:
        sections = (
            OllamaBriefSection(
                heading="Clinical Context",
                bullets=("Summarize the main academic question",),
            ),
            OllamaBriefSection(
                heading="Core Mechanism",
                bullets=("Highlight the primary finding or pathway",),
            ),
            OllamaBriefSection(
                heading="Practice Impact",
                bullets=("Explain why the result matters clinically",),
            ),
        )

    return OllamaFigureBrief(
        title=title_match.group(1) if title_match else "Academic Figure Brief",
        subtitle="Local SVG fallback generated through the Ollama runtime",
        sections=sections,
        footer=citation_match.group(1) if citation_match else "Academic Figures MCP",
        accent_color="#0F6CBD",
    )


def extract_canvas_size(prompt: str) -> tuple[int, int]:
    match = re.search(r"canvas:\s*(\d{2,5})x(\d{2,5})", prompt)
    if match is None:
        return (1024, 1536)
    return (int(match.group(1)), int(match.group(2)))


def render_svg_brief(*, brief: OllamaFigureBrief, width: int, height: int) -> str:
    margin = 48
    header_height = 180
    footer_height = 72
    usable_height = height - header_height - footer_height - margin * 2
    section_count = max(1, min(len(brief.sections), 4))
    section_gap = 22
    section_height = int((usable_height - section_gap * (section_count - 1)) / section_count)
    section_width = width - margin * 2

    svg_parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}">'
        ),
        '<rect width="100%" height="100%" fill="#F7F4ED"/>',
        f'<rect x="0" y="0" width="100%" height="16" fill="{escape_xml(brief.accent_color)}"/>',
        (
            f'<text x="{margin}" y="88" '
            'font-size="42" font-family="Segoe UI, Arial, sans-serif" '
            'font-weight="700" fill="#132238">'
            f"{escape_xml(brief.title)}</text>"
        ),
    ]

    subtitle_y = 128
    for index, line in enumerate(wrap(brief.subtitle, 60)[:2]):
        svg_parts.append(
            f'<text x="{margin}" y="{subtitle_y + index * 28}" '
            'font-size="22" font-family="Segoe UI, Arial, sans-serif" '
            f'fill="#36516F">{escape_xml(line)}</text>'
        )

    for index, section in enumerate(brief.sections[:section_count]):
        y = margin + header_height + index * (section_height + section_gap)
        svg_parts.append(
            f'<rect x="{margin}" y="{y}" rx="24" ry="24" '
            f'width="{section_width}" height="{section_height}" '
            'fill="#FFFFFF" stroke="#D6DCE5" stroke-width="2"/>'
        )
        svg_parts.append(
            f'<text x="{margin + 28}" y="{y + 44}" '
            'font-size="28" font-family="Segoe UI, Arial, sans-serif" '
            'font-weight="600" fill="#132238">'
            f"{escape_xml(section.heading)}</text>"
        )

        cursor_y = y + 84
        for bullet in section.bullets[:3]:
            wrapped_lines = wrap(bullet, 54)[:2] or [bullet]
            svg_parts.append(
                f'<circle cx="{margin + 36}" cy="{cursor_y - 8}" '
                f'r="6" fill="{escape_xml(brief.accent_color)}"/>'
            )
            for line_index, line in enumerate(wrapped_lines):
                svg_parts.append(
                    f'<text x="{margin + 56}" '
                    f'y="{cursor_y + line_index * 24}" '
                    'font-size="20" font-family="Segoe UI, Arial, sans-serif" '
                    f'fill="#24384F">{escape_xml(line)}</text>'
                )
            cursor_y += 24 * len(wrapped_lines) + 18

    svg_parts.append(
        f'<text x="{margin}" y="{height - 28}" '
        'font-size="18" font-family="Segoe UI, Arial, sans-serif" '
        f'fill="#5E6C7B">{escape_xml(brief.footer)}</text>'
    )
    svg_parts.append("</svg>")
    return "".join(svg_parts)


def _coerce_brief_section(raw_section: object, index: int) -> OllamaBriefSection:
    section = raw_section if isinstance(raw_section, dict) else {}
    heading = str(section.get("heading", f"Section {index + 1}"))
    bullets_raw = section.get("bullets", [])
    bullets_list = bullets_raw if isinstance(bullets_raw, list) else []
    bullets = tuple(str(item) for item in bullets_list[:3])
    if not bullets:
        bullets = ("Key information distilled from the academic brief",)
    return OllamaBriefSection(heading=heading, bullets=bullets)


def _data_url_for_image(*, image_bytes: bytes, mime_type: str) -> str:
    return f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
