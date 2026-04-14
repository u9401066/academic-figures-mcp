"""Configuration loader — reads from environment variables only."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

GOOGLE_PROVIDER = "google"
OPENROUTER_PROVIDER = "openrouter"
OLLAMA_PROVIDER = "ollama"
METADATA_SOURCE_PUBMED = "pubmed"
METADATA_SOURCE_FILE = "file"

_SUPPORTED_PROVIDERS = {GOOGLE_PROVIDER, OPENROUTER_PROVIDER, OLLAMA_PROVIDER}
_SUPPORTED_TRANSPORTS = {"stdio", "sse", "streamable-http"}
_SUPPORTED_METADATA_SOURCES = {METADATA_SOURCE_PUBMED, METADATA_SOURCE_FILE}


def _normalize_provider(value: str) -> str:
    provider = value.strip().lower()
    if provider in _SUPPORTED_PROVIDERS:
        return provider
    return GOOGLE_PROVIDER


def _normalize_metadata_source(value: str) -> str:
    source = value.strip().lower()
    if source in _SUPPORTED_METADATA_SOURCES:
        return source
    return METADATA_SOURCE_PUBMED


def _default_model_for(provider: str) -> str:
    if provider == OPENROUTER_PROVIDER:
        return "google/gemini-3.1-flash-image-preview"
    if provider == OLLAMA_PROVIDER:
        return "llava:latest"
    return "gemini-3.1-flash-image-preview"


def _high_fidelity_model_for(provider: str) -> str:
    if provider == OPENROUTER_PROVIDER:
        return "google/gemini-3-pro-image-preview"
    if provider == OLLAMA_PROVIDER:
        return "llava:latest"
    return "gemini-3-pro-image-preview"


def _low_latency_model_for(provider: str) -> str:
    if provider == OPENROUTER_PROVIDER:
        return "google/gemini-2.5-flash-image"
    if provider == OLLAMA_PROVIDER:
        return "llava:latest"
    return "gemini-2.5-flash-image"


def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int, minimum: int = 1, maximum: int = 10) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


def _env_float(name: str, default: float, minimum: float = 0.0, maximum: float = 600.0) -> float:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class GeminiConfig:
    provider: str = GOOGLE_PROVIDER
    google_api_key: str = ""
    openrouter_api_key: str = ""
    default_model: str = "gemini-3.1-flash-image-preview"
    high_fidelity_model: str = "gemini-3-pro-image-preview"
    low_latency_model: str = "gemini-2.5-flash-image"
    default_aspect_ratio: str = "3:4"
    default_image_size: str = "1K"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_http_referer: str = ""
    openrouter_app_title: str = "Academic Figures MCP"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llava:latest"
    request_timeout_seconds: float = 180.0
    max_attempts: int = 3
    retry_backoff_seconds: float = 1.0
    enable_provider_fallback: bool = True

    @property
    def api_key(self) -> str:
        if self.provider == OPENROUTER_PROVIDER:
            return self.openrouter_api_key
        if self.provider == GOOGLE_PROVIDER:
            return self.google_api_key
        return ""

    @property
    def is_openrouter(self) -> bool:
        return self.provider == OPENROUTER_PROVIDER

    @property
    def is_google(self) -> bool:
        return self.provider == GOOGLE_PROVIDER

    @property
    def is_ollama(self) -> bool:
        return self.provider == OLLAMA_PROVIDER

    @property
    def requires_api_key(self) -> bool:
        return self.provider in {GOOGLE_PROVIDER, OPENROUTER_PROVIDER}

    @property
    def required_api_key_env(self) -> str:
        if self.provider == OPENROUTER_PROVIDER:
            return "OPENROUTER_API_KEY"
        if self.provider == GOOGLE_PROVIDER:
            return "GOOGLE_API_KEY"
        return ""

    @property
    def fallback_provider(self) -> str | None:
        if not self.enable_provider_fallback:
            return None
        if self.provider == GOOGLE_PROVIDER and self.openrouter_api_key:
            return OPENROUTER_PROVIDER
        if self.provider == OPENROUTER_PROVIDER and self.google_api_key:
            return GOOGLE_PROVIDER
        return None


@dataclass(frozen=True)
class ServerConfig:
    transport: str = "stdio"
    output_dir: str = ".academic-figures/outputs"
    manifest_dir: str = ".academic-figures/manifests"
    metadata_source: str = METADATA_SOURCE_PUBMED
    metadata_file: str | None = None
    gemini: GeminiConfig = field(default_factory=GeminiConfig)


def load_config() -> ServerConfig:
    """Load configuration from environment variables.

    Required:
        GOOGLE_API_KEY — required when AFM_IMAGE_PROVIDER=google
        OPENROUTER_API_KEY — required when AFM_IMAGE_PROVIDER=openrouter

    Optional:
        AFM_IMAGE_PROVIDER — "google" | "openrouter" | "ollama" (default: google)
        MCP_TRANSPORT — "stdio" | "sse" | "streamable-http" (default: stdio)
        GEMINI_MODEL — override default model name
        GEMINI_HIGH_FIDELITY_MODEL — override pro model name
        GEMINI_LOW_LATENCY_MODEL — override low-latency model name
        GEMINI_IMAGE_SIZE — "0.5K" | "1K" | "2K" | "4K"
        AFM_OUTPUT_DIR — output directory (default: .academic-figures/outputs)
        AFM_MANIFEST_DIR — manifest directory (default: .academic-figures/manifests)
        AFM_METADATA_SOURCE — "pubmed" | "file" (default: pubmed)
        AFM_METADATA_FILE — JSON/YAML file used when AFM_METADATA_SOURCE=file
        OPENROUTER_BASE_URL — OpenRouter API base URL (default: https://openrouter.ai/api/v1)
        OPENROUTER_HTTP_REFERER — optional attribution header for OpenRouter
        OPENROUTER_APP_TITLE — optional app title header for OpenRouter
        OLLAMA_BASE_URL — OpenAI-compatible Ollama endpoint (default: http://localhost:11434/v1)
        OLLAMA_MODEL — local Ollama model used for planning/SVG generation/evaluation
        AFM_MAX_ATTEMPTS — retry attempts for transient provider failures (default: 3)
        AFM_RETRY_BACKOFF_SECONDS — exponential backoff base seconds (default: 1.0)
        AFM_REQUEST_TIMEOUT_SECONDS — HTTP timeout in seconds (default: 180)
        AFM_ENABLE_PROVIDER_FALLBACK — fallback between Google and
        OpenRouter when both are configured
    """
    provider = _normalize_provider(os.environ.get("AFM_IMAGE_PROVIDER", GOOGLE_PROVIDER))
    google_api_key = os.environ.get("GOOGLE_API_KEY", "")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
    ollama_model = os.environ.get("OLLAMA_MODEL", _default_model_for(OLLAMA_PROVIDER))

    gemini = GeminiConfig(
        provider=provider,
        google_api_key=google_api_key,
        openrouter_api_key=openrouter_api_key,
        default_model=os.environ.get(
            "GEMINI_MODEL",
            ollama_model if provider == OLLAMA_PROVIDER else _default_model_for(provider),
        ),
        high_fidelity_model=os.environ.get(
            "GEMINI_HIGH_FIDELITY_MODEL",
            _high_fidelity_model_for(provider),
        ),
        low_latency_model=os.environ.get(
            "GEMINI_LOW_LATENCY_MODEL",
            _low_latency_model_for(provider),
        ),
        default_aspect_ratio=os.environ.get(
            "GEMINI_ASPECT_RATIO",
            GeminiConfig.default_aspect_ratio,
        ),
        default_image_size=os.environ.get(
            "GEMINI_IMAGE_SIZE",
            GeminiConfig.default_image_size,
        ),
        openrouter_base_url=os.environ.get(
            "OPENROUTER_BASE_URL",
            GeminiConfig.openrouter_base_url,
        ),
        openrouter_http_referer=os.environ.get(
            "OPENROUTER_HTTP_REFERER",
            GeminiConfig.openrouter_http_referer,
        ),
        openrouter_app_title=os.environ.get(
            "OPENROUTER_APP_TITLE",
            GeminiConfig.openrouter_app_title,
        ),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", GeminiConfig.ollama_base_url),
        ollama_model=ollama_model,
        request_timeout_seconds=_env_float(
            "AFM_REQUEST_TIMEOUT_SECONDS",
            180.0,
            minimum=5.0,
        ),
        max_attempts=_env_int("AFM_MAX_ATTEMPTS", 3),
        retry_backoff_seconds=_env_float(
            "AFM_RETRY_BACKOFF_SECONDS",
            1.0,
            maximum=30.0,
        ),
        enable_provider_fallback=_env_flag("AFM_ENABLE_PROVIDER_FALLBACK", True),
    )

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport not in _SUPPORTED_TRANSPORTS:
        transport = "stdio"

    metadata_file = os.environ.get("AFM_METADATA_FILE", "").strip() or None

    return ServerConfig(
        transport=transport,
        output_dir=os.environ.get("AFM_OUTPUT_DIR", ".academic-figures/outputs"),
        manifest_dir=os.environ.get("AFM_MANIFEST_DIR", ".academic-figures/manifests"),
        metadata_source=_normalize_metadata_source(
            os.environ.get("AFM_METADATA_SOURCE", METADATA_SOURCE_PUBMED)
        ),
        metadata_file=metadata_file,
        gemini=gemini,
    )
