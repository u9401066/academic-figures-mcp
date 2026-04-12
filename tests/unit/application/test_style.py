"""Tests for Theme 4 — style extraction, application, and storage."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.application.style import (
    ApplyStyleRequest,
    ApplyStyleUseCase,
    ExtractStyleRequest,
    ExtractStyleUseCase,
    ListStylesRequest,
    ListStylesUseCase,
    _extract_hex_colors,
    _extract_section,
    _inject_style_into_prompt,
    _parse_style_profile,
)
from src.domain.entities import GenerationResult
from src.domain.exceptions import ImageNotFoundError, StyleNotFoundError
from src.domain.value_objects import StyleProfile
from src.infrastructure.style_store import FileStyleStore

# ── Parsing helpers ──────────────────────────────────────────────


def test_extract_hex_colors_finds_all_unique() -> None:
    text = "Primary: #FF0000, secondary: #00FF00, also #FF0000 repeated."
    colors = _extract_hex_colors(text)
    assert colors == ["#FF0000", "#00FF00"]


def test_extract_hex_colors_expands_shorthand() -> None:
    text = "Short: #FFF and #ABC"
    colors = _extract_hex_colors(text)
    assert "#FFFFFF" in colors
    assert "#AABBCC" in colors


def test_extract_section_returns_content() -> None:
    text = "TYPOGRAPHY: Sans-serif bold headings\nLAYOUT: Grid-based"
    result = _extract_section(text, "TYPOGRAPHY")
    assert "Sans-serif" in result


def test_parse_style_profile_builds_profile() -> None:
    raw = (
        "ONE-LINE DESCRIPTION: Clean clinical style\n"
        "COLOR PALETTE: #1A237E, #009688, #FFFFFF\n"
        "TYPOGRAPHY: Arial bold headers\n"
        "LAYOUT: Grid-based 2-column\n"
        "MOOD: Professional and clean"
    )
    profile = _parse_style_profile(raw_text=raw, source_image_path="/test.png")
    assert profile.description == "Clean clinical style"
    assert len(profile.color_palette) == 3
    assert profile.mood == "Professional and clean"


def test_inject_style_into_prompt_appends_block() -> None:
    profile = StyleProfile(
        style_id="abc",
        description="Bold style",
        color_palette=["#FF0000"],
        typography_hints="Sans-serif",
        layout_hints="Grid",
        mood="Bold",
    )
    result = _inject_style_into_prompt("Original prompt", profile)
    assert "STYLE PROFILE (reused)" in result
    assert "#FF0000" in result
    assert "Bold style" in result


# ── FileStyleStore tests ────────────────────────────────────────


def test_style_store_save_and_load(tmp_path: Path) -> None:
    store = FileStyleStore(str(tmp_path))
    profile = StyleProfile(
        style_id="test123",
        description="Test style",
        color_palette=["#AABBCC"],
        typography_hints="Mono",
        layout_hints="Single column",
        mood="Minimal",
        source_image_path="/img.png",
        raw_extraction_text="raw",
    )
    store.save(profile)
    loaded = store.load("test123")
    assert isinstance(loaded, StyleProfile)
    assert loaded.style_id == "test123"
    assert loaded.description == "Test style"
    assert loaded.color_palette == ["#AABBCC"]


def test_style_store_raises_on_missing(tmp_path: Path) -> None:
    store = FileStyleStore(str(tmp_path))
    with pytest.raises(StyleNotFoundError):
        store.load("nonexistent")


def test_style_store_lists_profiles(tmp_path: Path) -> None:
    store = FileStyleStore(str(tmp_path))
    for i in range(3):
        store.save(
            StyleProfile(
                style_id=f"s{i}",
                description=f"Style {i}",
            )
        )
    result = store.list(limit=10)
    assert len(result) == 3


# ── ExtractStyleUseCase tests ───────────────────────────────────


def test_extract_style_raises_on_missing_image(tmp_path: Path) -> None:
    mock_gen = MagicMock()
    store = FileStyleStore(str(tmp_path))
    uc = ExtractStyleUseCase(generator=mock_gen, style_store=store)
    with pytest.raises(ImageNotFoundError):
        uc.execute(ExtractStyleRequest(image_path="/nonexistent.png"))


def test_extract_style_returns_profile(tmp_path: Path) -> None:
    # Create a dummy image file
    img_path = tmp_path / "sample.png"
    img_path.write_bytes(b"fake image")

    mock_gen = MagicMock()
    mock_gen.edit.return_value = GenerationResult(
        text=(
            "ONE-LINE DESCRIPTION: Clean academic style\n"
            "COLOR PALETTE: #1A237E, #009688\n"
            "TYPOGRAPHY: Helvetica\n"
            "LAYOUT: Grid\n"
            "MOOD: Professional"
        ),
        model="test-model",
        elapsed_seconds=1.0,
    )
    store = FileStyleStore(str(tmp_path / "styles"))
    uc = ExtractStyleUseCase(generator=mock_gen, style_store=store)
    result = uc.execute(ExtractStyleRequest(image_path=str(img_path)))
    assert result["status"] == "ok"
    assert "style_id" in result
    assert len(result["color_palette"]) == 2  # type: ignore[arg-type]


# ── ApplyStyleUseCase tests ─────────────────────────────────────


def test_apply_style_generates_figure(tmp_path: Path) -> None:
    store = FileStyleStore(str(tmp_path / "styles"))
    profile = StyleProfile(
        style_id="apply_test",
        description="Bold academic",
        color_palette=["#FF0000"],
    )
    store.save(profile)

    mock_gen = MagicMock()
    mock_gen.generate.return_value = GenerationResult(
        image_bytes=b"styled-output",
        text="generated",
        model="test-model",
        elapsed_seconds=1.5,
    )

    uc = ApplyStyleUseCase(
        style_store=store,
        generator=mock_gen,
        output_dir=str(tmp_path / "output"),
    )
    payload: dict[str, Any] = {
        "prompt_pack": {"prompt": "Generate a figure"},
        "goal": "Test figure",
    }
    result = uc.execute(
        ApplyStyleRequest(
            style_id="apply_test",
            planned_payload=payload,
        )
    )
    assert result["status"] == "ok"
    assert result["style_id"] == "apply_test"
    assert "output_path" in result


# ── ListStylesUseCase tests ─────────────────────────────────────


def test_list_styles_returns_profiles(tmp_path: Path) -> None:
    store = FileStyleStore(str(tmp_path))
    store.save(StyleProfile(style_id="ls1", description="Style 1"))
    store.save(StyleProfile(style_id="ls2", description="Style 2"))

    uc = ListStylesUseCase(style_store=store)
    result = uc.execute(ListStylesRequest(limit=10))
    assert result["status"] == "ok"
    styles = result["styles"]
    assert isinstance(styles, list)
    assert len(styles) == 2
