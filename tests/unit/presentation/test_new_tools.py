"""Tests for the new MCP tools — poster and style endpoints."""

from __future__ import annotations

import pytest

from src.domain.exceptions import ValidationError
from src.presentation.validation import (
    normalize_layout_preset,
    normalize_poster_sections,
    normalize_style_id,
)

# ── Poster validation ────────────────────────────────────────────


def test_normalize_layout_preset_accepts_valid() -> None:
    assert normalize_layout_preset("portrait_a0") == "portrait_a0"
    assert normalize_layout_preset("landscape_a0") == "landscape_a0"
    assert normalize_layout_preset("tri_column") == "tri_column"


def test_normalize_layout_preset_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        normalize_layout_preset("fancy_layout")


def test_normalize_layout_preset_defaults_on_empty() -> None:
    assert normalize_layout_preset("") == "portrait_a0"


def test_normalize_poster_sections_accepts_valid() -> None:
    result = normalize_poster_sections([{"name": "intro", "content": "text"}])
    assert result is not None
    assert result[0]["name"] == "intro"


def test_normalize_poster_sections_rejects_missing_name() -> None:
    with pytest.raises(ValidationError):
        normalize_poster_sections([{"content": "no name"}])


def test_normalize_poster_sections_passes_none() -> None:
    assert normalize_poster_sections(None) is None


# ── Style validation ────────────────────────────────────────────


def test_normalize_style_id_accepts_valid() -> None:
    assert normalize_style_id("abc123") == "abc123"


def test_normalize_style_id_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        normalize_style_id("")


def test_normalize_style_id_rejects_too_long() -> None:
    with pytest.raises(ValidationError):
        normalize_style_id("a" * 201)
