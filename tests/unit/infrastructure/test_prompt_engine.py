from __future__ import annotations

from pathlib import Path

from src.infrastructure.prompt_engine import PromptEngine


def _template_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "templates"


def test_prompt_engine_injects_nature_profile() -> None:
    engine = PromptEngine(template_dir=str(_template_dir()))

    prompt, profile = engine.inject_journal_requirements(
        "base prompt",
        target_journal="Nature",
    )

    assert profile is not None
    assert profile["id"] == "nature_portfolio"
    assert "## Journal Profile" in prompt
    assert "Nature Portfolio" in prompt
    assert "89" in prompt


def test_prompt_engine_matches_nejm_abbreviation() -> None:
    engine = PromptEngine(template_dir=str(_template_dir()))

    prompt, profile = engine.inject_journal_requirements(
        "base prompt",
        source_journal="N Engl J Med",
    )

    assert profile is not None
    assert profile["id"] == "nejm"
    assert "editable vector files" in prompt
