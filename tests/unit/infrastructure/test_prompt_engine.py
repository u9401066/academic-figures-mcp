from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from src.domain.entities import Paper
from src.infrastructure import prompt_engine as prompt_engine_module
from src.infrastructure.prompt_engine import PromptEngine

if TYPE_CHECKING:
    from pytest import MonkeyPatch


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
    assert json.loads(json.dumps(profile)) == profile
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


def test_prompt_engine_resolves_installed_data_templates(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_package_file = tmp_path / "site-packages" / "src" / "infrastructure" / "prompt_engine.py"
    fake_package_file.parent.mkdir(parents=True)
    fake_package_file.write_text("", encoding="utf-8")
    data_templates = tmp_path / "venv-data" / "templates"
    data_templates.mkdir(parents=True)
    (data_templates / "prompt-templates.md").write_text(
        "### Template 1: General Infographic\nbody",
        encoding="utf-8",
    )
    (data_templates / "journal-profiles.yaml").write_text(
        "profiles:\n"
        "  - id: test_journal\n"
        "    display_name: Test Journal\n"
        "    aliases: [Test Journal]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(prompt_engine_module, "__file__", str(fake_package_file))
    monkeypatch.setattr(
        "src.infrastructure.prompt_engine.sysconfig.get_path",
        lambda name: str(tmp_path / "venv-data") if name == "data" else "",
    )

    engine = PromptEngine()
    prompt, profile = engine.inject_journal_requirements(
        "base prompt",
        target_journal="Test Journal",
    )

    assert engine.template_dir == data_templates
    assert profile is not None
    assert profile["id"] == "test_journal"
    assert "Test Journal" in prompt


def test_prompt_engine_builds_cjk_text_block_for_zh_tw() -> None:
    block = PromptEngine._build_cjk_text_block(
        language="zh-TW",
        expected_labels=["急性冠心症", "處置流程"],
    )

    assert "Block 8: CJK TEXT FIDELITY" in block
    assert "target_script: zh-TW" in block
    assert "「急性冠心症」" in block
    assert "「處置流程」" in block
    assert "Do NOT romanize" in block


def test_prompt_engine_omits_cjk_block_for_english() -> None:
    block = PromptEngine._build_cjk_text_block(
        language="en",
        expected_labels=["Title"],
    )

    assert block == ""


def test_prompt_engine_cjk_block_handles_missing_labels() -> None:
    block = PromptEngine._build_cjk_text_block(
        language="zh-TW",
        expected_labels=[],
    )

    assert "No specific labels provided" in block


def test_prompt_engine_build_prompt_includes_cjk_block() -> None:
    engine = PromptEngine()
    paper = Paper(
        pmid="12345678",
        title="Test Paper",
        authors="Author",
        journal="Journal",
        abstract="Test abstract",
    )

    prompt = engine.build_prompt(
        paper=paper,
        figure_type="infographic",
        language="zh-TW",
        output_size="1024x1536",
        expected_labels=["急性冠心症", "治療流程"],
    )

    assert "Block 8: CJK TEXT FIDELITY" in prompt
    assert "「急性冠心症」" in prompt


def test_prompt_engine_build_prompt_skips_cjk_block_for_english() -> None:
    engine = PromptEngine()
    paper = Paper(
        pmid="12345678",
        title="Test Paper",
        authors="Author",
        journal="Journal",
        abstract="Test abstract",
    )

    prompt = engine.build_prompt(
        paper=paper,
        figure_type="infographic",
        language="en",
        output_size="1024x1536",
        expected_labels=["Title", "Header"],
    )

    assert "Block 8" not in prompt
