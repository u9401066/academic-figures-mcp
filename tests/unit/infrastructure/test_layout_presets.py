"""Tests for Theme 2 — panel layout presets and label rules."""

from __future__ import annotations

from src.domain.value_objects import (
    LAYOUT_PRESET_CONFIGS,
    LayoutPreset,
    PanelLabelStyle,
    resolve_layout_preset,
)
from src.infrastructure.composite import _generate_label, _resolve_grid


def test_resolve_layout_preset_returns_known_presets() -> None:
    for preset in LayoutPreset:
        result = resolve_layout_preset(preset.value)
        assert result is not None
        assert "description" in result


def test_resolve_layout_preset_returns_none_for_unknown() -> None:
    assert resolve_layout_preset("nonexistent") is None


def test_grid_2x2_returns_2_cols_2_rows() -> None:
    cols, rows = _resolve_grid(4, LayoutPreset.GRID_2X2)
    assert cols == 2
    assert rows == 2


def test_horizontal_strip_returns_single_row() -> None:
    cols, rows = _resolve_grid(3, LayoutPreset.HORIZONTAL_STRIP)
    assert rows == 1
    assert cols == 3


def test_vertical_strip_returns_single_col() -> None:
    cols, rows = _resolve_grid(3, LayoutPreset.VERTICAL_STRIP)
    assert cols == 1
    assert rows == 3


def test_resolve_grid_auto_balances_panels() -> None:
    cols, rows = _resolve_grid(6, None)
    assert cols == 3
    assert rows == 2
    assert cols * rows >= 6


def test_generate_label_uppercase() -> None:
    assert _generate_label(0, PanelLabelStyle.UPPERCASE) == "A"
    assert _generate_label(2, PanelLabelStyle.UPPERCASE) == "C"


def test_generate_label_lowercase() -> None:
    assert _generate_label(0, PanelLabelStyle.LOWERCASE) == "a"
    assert _generate_label(1, PanelLabelStyle.LOWERCASE) == "b"


def test_generate_label_numeric() -> None:
    assert _generate_label(0, PanelLabelStyle.NUMERIC) == "1"
    assert _generate_label(4, PanelLabelStyle.NUMERIC) == "5"


def test_generate_label_roman() -> None:
    assert _generate_label(0, PanelLabelStyle.ROMAN) == "I"
    assert _generate_label(3, PanelLabelStyle.ROMAN) == "IV"


def test_generate_label_none() -> None:
    assert _generate_label(0, PanelLabelStyle.NONE) == ""


def test_layout_preset_configs_have_required_fields() -> None:
    for name, cfg in LAYOUT_PRESET_CONFIGS.items():
        assert "description" in cfg, f"{name} missing description"
        assert "columns" in cfg or "rows" in cfg, f"{name} missing columns/rows"
