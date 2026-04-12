"""Tests for Theme 3 — poster workflow use cases."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from src.application.poster import (
    GeneratePosterRequest,
    GeneratePosterUseCase,
    PlanPosterRequest,
    PlanPosterUseCase,
    validate_poster_content,
)
from src.domain.entities import GenerationResult, Paper
from src.domain.exceptions import PosterValidationError
from src.domain.value_objects import POSTER_LAYOUT_CONFIGS

# ── Guardrail tests ─────────────────────────────────────────────


def test_validate_poster_content_passes_for_normal_content() -> None:
    warnings = validate_poster_content(
        title="A short title",
        sections=[{"name": "intro", "content": "Some content"}],
    )
    assert warnings == []


def test_validate_poster_content_warns_on_long_title() -> None:
    long_title = "A" * 200
    warnings = validate_poster_content(title=long_title, sections=[])
    assert any("Title exceeds" in w for w in warnings)


def test_validate_poster_content_warns_on_too_many_sections() -> None:
    sections = [{"name": f"s{i}", "content": ""} for i in range(20)]
    warnings = validate_poster_content(title="ok", sections=sections)
    assert any("More than" in w for w in warnings)


def test_validate_poster_content_warns_on_long_section() -> None:
    sections = [{"name": "intro", "content": "x" * 2000}]
    warnings = validate_poster_content(title="ok", sections=sections)
    assert any("exceeds" in w for w in warnings)


# ── Plan poster tests ───────────────────────────────────────────


def _make_fetcher(paper: Paper | None = None) -> Any:
    mock = MagicMock()
    mock.fetch_paper.return_value = paper or Paper(
        pmid="12345",
        title="Test Poster Paper",
        authors="Author A",
        journal="Test Journal",
        abstract="This is a short abstract for testing.",
    )
    return mock


def _make_prompt_builder() -> Any:
    mock = MagicMock()
    mock.build_prompt.return_value = "mock prompt"
    mock.inject_journal_requirements.return_value = ("mock prompt", None)
    return mock


def test_plan_poster_returns_planned_payload() -> None:
    uc = PlanPosterUseCase(
        fetcher=_make_fetcher(),
        prompt_builder=_make_prompt_builder(),
        provider_name="google",
    )
    result = uc.execute(PlanPosterRequest(pmid="12345"))
    assert result["status"] == "ok"
    assert "planned_payload" in result
    payload = result["planned_payload"]
    assert isinstance(payload, dict)
    assert payload["asset_kind"] == "poster"
    assert payload["layout_preset"] == "portrait_a0"


def test_plan_poster_rejects_over_dense_content() -> None:
    uc = PlanPosterUseCase(
        fetcher=_make_fetcher(),
        prompt_builder=_make_prompt_builder(),
        provider_name="google",
    )
    long_sections = [{"name": f"s{i}", "content": "x" * 2000} for i in range(3)]
    with pytest.raises(PosterValidationError):
        uc.execute(PlanPosterRequest(pmid="12345", sections=long_sections))


# ── Generate poster tests ───────────────────────────────────────


def test_generate_poster_from_payload_succeeds() -> None:
    mock_gen = MagicMock()
    mock_gen.generate.return_value = GenerationResult(
        image_bytes=b"fake-poster-png",
        text="poster generated",
        model="test-model",
        elapsed_seconds=2.0,
    )
    uc = GeneratePosterUseCase(
        fetcher=_make_fetcher(),
        generator=mock_gen,
        prompt_builder=_make_prompt_builder(),
        output_dir="/tmp/poster-test-output",
    )
    payload: dict[str, Any] = {
        "asset_kind": "poster",
        "title": "Test Poster",
        "layout_preset": "portrait_a0",
        "prompt_pack": {"prompt": "generate a poster"},
    }
    result = uc.execute(GeneratePosterRequest(planned_payload=payload))
    assert result["status"] == "ok"
    assert result["generation_contract"] == "poster"
    assert "output_path" in result


def test_generate_poster_reports_failure() -> None:
    mock_gen = MagicMock()
    mock_gen.generate.return_value = GenerationResult(
        image_bytes=None,
        error="provider error",
    )
    uc = GeneratePosterUseCase(
        fetcher=_make_fetcher(),
        generator=mock_gen,
        prompt_builder=_make_prompt_builder(),
        output_dir="/tmp/poster-test-output",
    )
    payload: dict[str, Any] = {
        "asset_kind": "poster",
        "title": "Fail Poster",
        "prompt_pack": {"prompt": "fail"},
    }
    result = uc.execute(GeneratePosterRequest(planned_payload=payload))
    assert result["status"] == "generation_failed"


def test_poster_layout_configs_contain_required_fields() -> None:
    for name, cfg in POSTER_LAYOUT_CONFIGS.items():
        assert "width_px" in cfg, f"{name} missing width_px"
        assert "height_px" in cfg, f"{name} missing height_px"
        assert "dpi" in cfg, f"{name} missing dpi"
        assert "columns" in cfg, f"{name} missing columns"
