"""Multi-provider figure adapter with retry, fallback, and local Ollama support."""

from __future__ import annotations

import base64
import contextlib
import json
import re
import time
from dataclasses import dataclass, replace
from html import escape as escape_xml
from textwrap import wrap
from typing import TYPE_CHECKING, Any, TypeVar, cast

import httpx
from google import genai
from google.genai import types

from src.domain.entities import GenerationResult
from src.domain.interfaces import ImageGenerator
from src.infrastructure.config import OLLAMA_PROVIDER, OPENROUTER_PROVIDER

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from src.infrastructure.config import GeminiConfig

T = TypeVar("T")


class GeminiAdapter(ImageGenerator):
    """Wraps Google, OpenRouter, and Ollama-backed figure workflows."""

    def __init__(self, config: GeminiConfig) -> None:
        self._config = config
        self._client = None if not config.is_google else genai.Client(api_key=config.api_key)

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        aspect_ratio: str | None = None,
    ) -> GenerationResult:
        model_name = model or self._config.default_model
        ar = aspect_ratio or self._config.default_aspect_ratio
        start = time.time()

        if self._config.is_ollama:
            return self._generate_via_ollama(prompt=prompt, model_name=model_name, start=start)
        if self._config.is_openrouter:
            return self._generate_via_openrouter(
                prompt=prompt,
                model_name=model_name,
                aspect_ratio=ar,
                start=start,
            )
        return self._generate_via_google(
            prompt=prompt,
            model_name=model_name,
            aspect_ratio=ar,
            start=start,
        )

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
            return GenerationResult(
                model=model_name,
                elapsed_seconds=round(time.time() - start, 2),
                error=f"Image not found: {image_path}",
            )

        img_bytes = image_path.read_bytes()
        mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

        if self._config.is_ollama:
            return self._edit_via_ollama(
                image_bytes=img_bytes,
                mime_type=mime,
                instruction=instruction,
                model_name=model_name,
                start=start,
            )
        if self._config.is_openrouter:
            return self._edit_via_openrouter(
                image_bytes=img_bytes,
                mime_type=mime,
                instruction=instruction,
                model_name=model_name,
                start=start,
            )
        return self._edit_via_google(
            image_bytes=img_bytes,
            mime_type=mime,
            instruction=instruction,
            model_name=model_name,
            start=start,
        )

    def create_edit_session(self, *, model: str | None = None) -> EditSession:
        model_name = model or self._config.default_model
        if not self._config.is_google:
            raise ValueError(
                "Multi-turn edit sessions are only supported for the direct Google provider."
            )
        chat = self._google_client().chats.create(model=model_name)
        return EditSession(chat=chat, model=model_name)

    def _generate_via_google(
        self,
        *,
        prompt: str,
        model_name: str,
        aspect_ratio: str,
        start: float,
    ) -> GenerationResult:
        image_config: dict[str, str] = {"aspect_ratio": aspect_ratio}
        image_size = self._google_image_size()
        if image_size:
            image_config["image_size"] = image_size

        response, error = self._call_with_retry(
            lambda: self._google_client().models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=cast("Any", image_config),
                ),
            )
        )
        if error is not None or response is None:
            fallback = self._maybe_provider_fallback_generate(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                error=error or "Google provider failed",
            )
            if fallback is not None:
                return fallback
            return GenerationResult(
                model=model_name,
                elapsed_seconds=round(time.time() - start, 2),
                error=error or "Google provider failed",
            )

        return self._parse_response(response, model_name, start)

    def _edit_via_google(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> GenerationResult:
        response, error = self._call_with_retry(
            lambda: self._google_client().models.generate_content(
                model=model_name,
                contents=cast(
                    "Any",
                    [instruction, types.Part.from_bytes(data=image_bytes, mime_type=mime_type)],
                ),
                config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
            )
        )
        if error is not None or response is None:
            fallback = self._maybe_provider_fallback_edit(
                image_bytes=image_bytes,
                mime_type=mime_type,
                instruction=instruction,
                error=error or "Google provider failed",
            )
            if fallback is not None:
                return fallback
            return GenerationResult(
                model=model_name,
                elapsed_seconds=round(time.time() - start, 2),
                error=error or "Google provider failed",
            )

        return self._parse_response(response, model_name, start)

    def _generate_via_openrouter(
        self,
        *,
        prompt: str,
        model_name: str,
        aspect_ratio: str,
        start: float,
    ) -> GenerationResult:
        payload: dict[str, object] = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
            "image_config": self._openrouter_image_config(aspect_ratio),
        }
        data, error = self._request_json_with_retry(
            endpoint=self._openrouter_endpoint(),
            headers=self._openrouter_headers(),
            payload=payload,
        )
        if error is not None or data is None:
            fallback = self._maybe_provider_fallback_generate(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                error=error or "OpenRouter provider failed",
            )
            if fallback is not None:
                return fallback
            return GenerationResult(
                model=model_name,
                elapsed_seconds=round(time.time() - start, 2),
                error=error or "OpenRouter provider failed",
            )

        return self._parse_openrouter_response(data=data, model_name=model_name, start=start)

    def _edit_via_openrouter(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> GenerationResult:
        image_data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
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
            "image_config": self._openrouter_image_config(self._config.default_aspect_ratio),
        }
        data, error = self._request_json_with_retry(
            endpoint=self._openrouter_endpoint(),
            headers=self._openrouter_headers(),
            payload=payload,
        )
        if error is not None or data is None:
            fallback = self._maybe_provider_fallback_edit(
                image_bytes=image_bytes,
                mime_type=mime_type,
                instruction=instruction,
                error=error or "OpenRouter provider failed",
            )
            if fallback is not None:
                return fallback
            return GenerationResult(
                model=model_name,
                elapsed_seconds=round(time.time() - start, 2),
                error=error or "OpenRouter provider failed",
            )

        return self._parse_openrouter_response(data=data, model_name=model_name, start=start)

    def _generate_via_ollama(
        self,
        *,
        prompt: str,
        model_name: str,
        start: float,
    ) -> GenerationResult:
        text, error = self._ollama_chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You convert academic figure briefs into strict JSON "
                        "for an SVG renderer. Return JSON only with keys title, "
                        "subtitle, sections, footer, accent_color."
                    ),
                },
                {"role": "user", "content": self._ollama_generation_instruction(prompt)},
            ],
            model_name=model_name,
        )
        if error is not None:
            return GenerationResult(
                model=model_name,
                elapsed_seconds=round(time.time() - start, 2),
                error=error,
            )

        brief = self._parse_ollama_brief(text) or self._brief_from_prompt(prompt)
        width, height = self._extract_canvas_size(prompt)
        svg = self._render_svg_brief(brief=brief, width=width, height=height)
        return GenerationResult(
            image_bytes=svg.encode("utf-8"),
            text=text,
            model=model_name,
            elapsed_seconds=round(time.time() - start, 2),
            media_type="image/svg+xml",
        )

    def _edit_via_ollama(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        model_name: str,
        start: float,
    ) -> GenerationResult:
        image_data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        text, error = self._ollama_chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You review academic figures for structure, scientific "
                        "clarity, and publication quality. If asked to evaluate, "
                        "return concise scores and issues."
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
        if error is not None:
            return GenerationResult(
                model=model_name,
                elapsed_seconds=round(time.time() - start, 2),
                error=error,
            )
        if self._looks_like_evaluation_instruction(instruction):
            return GenerationResult(
                text=text,
                model=model_name,
                elapsed_seconds=round(time.time() - start, 2),
            )
        return GenerationResult(
            text=text,
            model=model_name,
            elapsed_seconds=round(time.time() - start, 2),
            error=(
                "Ollama runtime currently supports planning, local SVG "
                "generation, and vision-based evaluation, but not bitmap "
                "image editing."
            ),
        )

    def _ollama_chat(
        self,
        *,
        messages: list[dict[str, object]],
        model_name: str,
    ) -> tuple[str, str | None]:
        payload: dict[str, object] = {
            "model": model_name,
            "messages": messages,
        }
        data, error = self._request_json_with_retry(
            endpoint=self._ollama_endpoint(),
            headers={"Content-Type": "application/json"},
            payload=payload,
        )
        if error is not None or data is None:
            return "", error or "Ollama request failed"
        message_text = self._extract_message_text(data)
        if not message_text:
            return "", "No text returned by Ollama"
        return message_text, None

    def _ollama_generation_instruction(self, prompt: str) -> str:
        return (
            "Summarize this academic figure brief into compact JSON. "
            "Create 3 to 5 sections, each with a short heading and 1 to 2 bullets. "
            "Keep all text publication-safe and concise. Return JSON only.\n\n"
            f"{prompt}"
        )

    def _parse_ollama_brief(self, text: str) -> dict[str, object] | None:
        first = text.find("{")
        last = text.rfind("}")
        if first == -1 or last == -1 or last <= first:
            return None
        try:
            parsed = json.loads(text[first : last + 1])
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _brief_from_prompt(self, prompt: str) -> dict[str, object]:
        title_match = re.search(r"title:\s*'([^']+)'", prompt)
        citation_match = re.search(r"citation:\s*'([^']+)'", prompt)
        sections_match = re.search(r"sections:\s*(.+)", prompt)
        section_tokens = []
        if sections_match:
            raw_sections = sections_match.group(1)
            section_tokens = [
                token.strip(" -") for token in re.split(r"→|,", raw_sections) if token.strip()
            ]

        sections = [
            {
                "heading": token.title(),
                "bullets": ["Key information distilled from the academic brief"],
            }
            for token in section_tokens[:4]
        ]
        if not sections:
            sections = [
                {
                    "heading": "Clinical Context",
                    "bullets": ["Summarize the main academic question"],
                },
                {
                    "heading": "Core Mechanism",
                    "bullets": ["Highlight the primary finding or pathway"],
                },
                {
                    "heading": "Practice Impact",
                    "bullets": ["Explain why the result matters clinically"],
                },
            ]

        return {
            "title": title_match.group(1) if title_match else "Academic Figure Brief",
            "subtitle": "Local SVG fallback generated through the Ollama runtime",
            "sections": sections,
            "footer": citation_match.group(1) if citation_match else "Academic Figures MCP",
            "accent_color": "#0F6CBD",
        }

    def _extract_canvas_size(self, prompt: str) -> tuple[int, int]:
        match = re.search(r"canvas:\s*(\d{2,5})x(\d{2,5})", prompt)
        if match is None:
            return (1024, 1536)
        return (int(match.group(1)), int(match.group(2)))

    def _render_svg_brief(self, *, brief: dict[str, object], width: int, height: int) -> str:
        title = str(brief.get("title", "Academic Figure"))
        subtitle = str(brief.get("subtitle", "Structured local rendering"))
        footer = str(brief.get("footer", "Academic Figures MCP"))
        accent = str(brief.get("accent_color", "#0F6CBD"))
        raw_sections = brief.get("sections", [])
        sections = raw_sections if isinstance(raw_sections, list) else []

        margin = 48
        header_height = 180
        footer_height = 72
        usable_height = height - header_height - footer_height - margin * 2
        section_count = max(1, min(len(sections), 4))
        section_gap = 22
        section_height = int((usable_height - section_gap * (section_count - 1)) / section_count)
        section_width = width - margin * 2

        svg_parts = [
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                f'height="{height}" viewBox="0 0 {width} {height}">'
            ),
            '<rect width="100%" height="100%" fill="#F7F4ED"/>',
            f'<rect x="0" y="0" width="100%" height="16" fill="{escape_xml(accent)}"/>',
            (
                f'<text x="{margin}" y="88" '
                'font-size="42" font-family="Segoe UI, Arial, sans-serif" '
                'font-weight="700" fill="#132238">'
                f"{escape_xml(title)}</text>"
            ),
        ]

        subtitle_y = 128
        for index, line in enumerate(wrap(subtitle, 60)[:2]):
            svg_parts.append(
                f'<text x="{margin}" y="{subtitle_y + index * 28}" '
                'font-size="22" font-family="Segoe UI, Arial, sans-serif" '
                f'fill="#36516F">{escape_xml(line)}</text>'
            )

        for index, raw_section in enumerate(sections[:section_count]):
            section = raw_section if isinstance(raw_section, dict) else {}
            heading = str(section.get("heading", f"Section {index + 1}"))
            bullets_raw = section.get("bullets", [])
            bullets = bullets_raw if isinstance(bullets_raw, list) else []
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
                f"{escape_xml(heading)}</text>"
            )

            cursor_y = y + 84
            for bullet in bullets[:3]:
                bullet_text = str(bullet)
                wrapped_lines = wrap(bullet_text, 54)[:2] or [bullet_text]
                svg_parts.append(
                    f'<circle cx="{margin + 36}" cy="{cursor_y - 8}" '
                    f'r="6" fill="{escape_xml(accent)}"/>'
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
            f'fill="#5E6C7B">{escape_xml(footer)}</text>'
        )
        svg_parts.append("</svg>")
        return "".join(svg_parts)

    def _request_json_with_retry(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, object],
    ) -> tuple[dict[str, object] | None, str | None]:
        response, error = self._call_with_retry(
            lambda: httpx.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self._config.request_timeout_seconds,
            )
        )
        if error is not None or response is None:
            return None, error

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return None, str(exc)

        try:
            data = response.json()
        except ValueError as exc:
            return None, str(exc)
        return data if isinstance(data, dict) else None, None

    def _call_with_retry(self, operation: Callable[[], T]) -> tuple[T | None, str | None]:
        last_error: Exception | None = None
        for attempt in range(1, self._config.max_attempts + 1):
            try:
                return operation(), None
            except Exception as exc:
                last_error = exc
                if attempt >= self._config.max_attempts or not self._is_retryable_error(exc):
                    break
                time.sleep(self._retry_delay(attempt))
        return None, str(last_error) if last_error is not None else "Unknown provider error"

    def _retry_delay(self, attempt: int) -> float:
        return float(min(self._config.retry_backoff_seconds * (2 ** max(0, attempt - 1)), 8.0))

    def _is_retryable_error(self, exc: Exception) -> bool:
        if isinstance(
            exc,
            (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.RemoteProtocolError,
            ),
        ):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in {408, 409, 425, 429, 500, 502, 503, 504}

        lowered = str(exc).lower()
        return any(
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
        )

    def _maybe_provider_fallback_generate(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        error: str,
    ) -> GenerationResult | None:
        fallback_adapter = self._fallback_adapter(error)
        if fallback_adapter is None:
            return None
        return fallback_adapter.generate(prompt=prompt, aspect_ratio=aspect_ratio)

    def _maybe_provider_fallback_edit(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        instruction: str,
        error: str,
    ) -> GenerationResult | None:
        fallback_adapter = self._fallback_adapter(error)
        if fallback_adapter is None:
            return None

        import tempfile
        from pathlib import Path

        temp_suffix = ".png" if mime_type == "image/png" else ".jpg"
        with tempfile.NamedTemporaryFile(suffix=temp_suffix, delete=False) as handle:
            handle.write(image_bytes)
            temp_path = Path(handle.name)
        try:
            return fallback_adapter.edit(temp_path, instruction)
        finally:
            with contextlib.suppress(OSError):
                temp_path.unlink(missing_ok=True)

    def _fallback_adapter(self, error: str) -> GeminiAdapter | None:
        fallback_provider = self._config.fallback_provider
        if fallback_provider is None or not self._looks_retryable_message(error):
            return None
        fallback_config = replace(
            self._config,
            provider=fallback_provider,
            default_model=self._provider_default_model(fallback_provider),
            high_fidelity_model=self._provider_high_fidelity_model(fallback_provider),
            low_latency_model=self._provider_low_latency_model(fallback_provider),
            enable_provider_fallback=False,
        )
        return GeminiAdapter(fallback_config)

    def _looks_retryable_message(self, error: str) -> bool:
        lowered = error.lower()
        return any(
            token in lowered
            for token in (
                "429",
                "quota",
                "rate limit",
                "resource_exhausted",
                "timeout",
                "503",
                "502",
            )
        )

    def _provider_default_model(self, provider: str) -> str:
        if provider == OPENROUTER_PROVIDER:
            return "google/gemini-3.1-flash-image-preview"
        if provider == OLLAMA_PROVIDER:
            return self._config.ollama_model
        return "gemini-3.1-flash-image-preview"

    def _provider_high_fidelity_model(self, provider: str) -> str:
        if provider == OPENROUTER_PROVIDER:
            return "google/gemini-3-pro-image-preview"
        if provider == OLLAMA_PROVIDER:
            return self._config.ollama_model
        return "gemini-3-pro-image-preview"

    def _provider_low_latency_model(self, provider: str) -> str:
        if provider == OPENROUTER_PROVIDER:
            return "google/gemini-2.5-flash-image"
        if provider == OLLAMA_PROVIDER:
            return self._config.ollama_model
        return "gemini-2.5-flash-image"

    def _extract_message_text(self, data: dict[str, object]) -> str:
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

    def _looks_like_evaluation_instruction(self, instruction: str) -> bool:
        lowered = instruction.lower()
        return any(
            token in lowered for token in ("evaluate this", "overall score", "critical issues")
        )

    def _parse_openrouter_response(
        self,
        *,
        data: dict[str, object],
        model_name: str,
        start: float,
    ) -> GenerationResult:
        text = self._extract_message_text(data)

        image_bytes: bytes | None = None
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
                    image_bytes = base64.b64decode(image_url.split(",", 1)[1])
                    break
                except Exception:
                    image_bytes = None

        elapsed = round(time.time() - start, 2)
        if image_bytes is None:
            return GenerationResult(
                model=model_name,
                text=text,
                elapsed_seconds=elapsed,
                error="No image returned by OpenRouter image model",
            )

        return GenerationResult(
            image_bytes=image_bytes,
            text=text,
            model=model_name,
            elapsed_seconds=elapsed,
            media_type="image/png",
        )

    def _parse_response(
        self,
        response: types.GenerateContentResponse,
        model_name: str,
        start: float,
    ) -> GenerationResult:
        image_bytes: bytes | None = None
        text_parts: list[str] = []

        for part in self._response_parts(response):
            if getattr(part, "inline_data", None) is not None:
                image_bytes = part.inline_data.data
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
            media_type="image/png",
        )

    def _response_parts(self, response: types.GenerateContentResponse) -> list[Any]:
        return list(getattr(response, "parts", []) or [])


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

        image_bytes: bytes | None = None
        text_parts: list[str] = []

        for part in getattr(response, "parts", []) or []:
            if getattr(part, "inline_data", None) is not None:
                image_bytes = part.inline_data.data
            elif getattr(part, "text", None) is not None:
                text_parts.append(part.text)

        elapsed = time.time() - start
        return GenerationResult(
            image_bytes=image_bytes,
            text="\n".join(text_parts),
            model=self.model,
            elapsed_seconds=round(elapsed, 2),
            error="" if image_bytes else "No image returned",
        )
